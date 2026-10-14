"""Contract-level lightweight fake GenLayer module, not a GenVM substitute."""
from __future__ import annotations
import importlib.util
import json
import sys
import types
import pytest
from pathlib import Path
from datetime import datetime, timezone

# GenLayer v0.6 exec_prompt(response_format="json") decodes a JSON string;
# Direct Mode's mock helper returns an already-parsed Python object. Adapt that
# mock response to the documented SDK wire shape without replacing the runner.
from gltest.direct import wasi_mock as _direct_wasi_mock

_original_direct_llm = _direct_wasi_mock._handle_llm_request

def _direct_llm_json_wire(vm, data):
    response = _original_direct_llm(vm, data)
    if (
        data.get('response_format') == 'json'
        and isinstance(response, dict)
        and isinstance(response.get('ok'), (dict, list))
    ):
        response = {**response, 'ok': json.dumps(response['ok'], separators=(',', ':'))}
    return response

_direct_wasi_mock._handle_llm_request = _direct_llm_json_wire

# genlayer-test 0.30.0rc2 leaves fd 0 open on Windows while it immediately
# unlinks the temporary message file. POSIX permits that unlink; Windows does
# not. Defer only that cleanup until the official Direct Mode VM restores fd 0.
if sys.platform == 'win32':
    from gltest.direct import loader as _direct_loader
    from gltest.direct.vm import VMContext as _VMContext

    def _inject_message_windows(vm):
        import os
        import tempfile
        from genlayer import calldata
        from genlayer.types import Address

        def address(value):
            return Address(value) if isinstance(value, bytes) else value

        message_data = {
            'contract_address': address(vm._contract_address),
            'sender_address': address(vm.sender),
            'origin_address': address(vm.origin),
            'stack': [],
            'value': vm._value,
            'datetime': vm._datetime,
            'is_init': False,
            'chain_id': vm._chain_id,
            'entry_kind': 0,
            'entry_data': b'',
            'entry_stage_data': None,
        }
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, calldata.encode(message_data))
            os.lseek(fd, 0, os.SEEK_SET)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(fd, 0)
            vm._direct_message_path = path
        except Exception:
            os.close(fd)
            os.unlink(path)
            raise
        else:
            os.close(fd)

    _direct_loader._inject_message_to_fd0 = _inject_message_windows
    _original_direct_cleanup = _VMContext._cleanup_after_deactivate

    def _cleanup_direct_message_windows(vm):
        try:
            _original_direct_cleanup(vm)
        finally:
            path = getattr(vm, '_direct_message_path', None)
            if path:
                Path(path).unlink(missing_ok=True)
                vm._direct_message_path = None

    _VMContext._cleanup_after_deactivate = _cleanup_direct_message_windows

ADDRS = ['0x' + format(k, '040x') for k in range(1, 15)]

class Revert(Exception):
    pass

class Return:
    def __init__(self, calldata):
        self.calldata = calldata

class FakeRecipient:
    transfers = []
    def __init__(self, address):
        self.address = address
    def emit_transfer(self, value):
        self.transfers.append((self.address, value))

class Provider:
    def __init__(self):
        self.body_by_url = {}
        self.validator_body_by_url = {}
        self.status_by_url = {}
        self.read_counts = {}
        self.answer = None
        self.validator_answer = None
    def render(self, url, mode='text'):
        return self.body_by_url[url]
    def get(self, url):
        count = self.read_counts.get(url, 0)
        self.read_counts[url] = count + 1
        body = self.validator_body_by_url.get(url, self.body_by_url[url]) if count > 0 else self.body_by_url[url]
        return types.SimpleNamespace(status_code=self.status_by_url.get(url, 200), body=body.encode('utf-8'))
    def exec_prompt(self, prompt, response_format='json'):
        assert response_format == 'json'
        return self.answer

class FakeVM:
    UserError = Revert
    Return = Return
    Result = object
    def __init__(self, provider):
        self.provider = provider
        self.disagree = False
    def run_nondet(self, leader, validator):
        result = leader()
        if self.disagree:
            raise RuntimeError('consensus mismatch')
        candidate = self.provider.validator_answer if self.provider.validator_answer is not None else result
        assert validator(Return(candidate)), 'validator rejected'
        return result

@pytest.fixture
def env(monkeypatch):
    provider = Provider()
    vm = FakeVM(provider)
    class Write:
        def __call__(self, f): return f
        def payable(self, f): return f
    public = types.SimpleNamespace(view=lambda f:f, write=Write())
    gl = types.ModuleType('genlayer')
    gl.Contract = object
    gl.TreeMap = dict
    gl.public = public
    gl.vm = vm
    gl.nondet = types.SimpleNamespace(web=provider, exec_prompt=provider.exec_prompt)
    gl.message = types.SimpleNamespace(sender_address=ADDRS[0], value=0)
    def interface(cls):
        return FakeRecipient
    gl.evm = types.SimpleNamespace(contract_interface=interface)
    types_module = types.ModuleType('genlayer.types')
    types_module.Address = str
    types_module.u256 = int
    storage_module = types.ModuleType('genlayer.storage.tree_map')
    storage_module.TreeMap = dict
    gl.__path__ = []
    contract_module = types.ModuleType('genlayer.contract')
    class FakeContract:
        def __new__(cls, *args, **kwargs):
            instance = super().__new__(cls)
            instance.bonds = {}
            instance.bond_ids_json = '[]'
            return instance
    contract_module.Contract = FakeContract
    monkeypatch.setitem(sys.modules, 'genlayer', gl)
    monkeypatch.setitem(sys.modules, 'genlayer.contract', contract_module)
    monkeypatch.setitem(sys.modules, 'genlayer.types', types_module)
    monkeypatch.setitem(sys.modules, 'genlayer.storage', types.ModuleType('genlayer.storage'))
    monkeypatch.setitem(sys.modules, 'genlayer.storage.tree_map', storage_module)
    path = Path(__file__).resolve().parents[1] / 'contracts' / 'bermond.py'
    spec = importlib.util.spec_from_file_location('bermond_contract_under_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fake_time = {'now': 1_800_000_000}
    monkeypatch.setattr(mod, 'now_seconds', lambda: fake_time['now'])
    FakeRecipient.transfers = []
    return types.SimpleNamespace(mod=mod, gl=gl, provider=provider, vm=vm, time=fake_time, transfers=FakeRecipient.transfers)
