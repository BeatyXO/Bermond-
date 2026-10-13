"""Contract-level lightweight fake GenLayer module, not a GenVM substitute."""
from __future__ import annotations
import importlib.util
import sys
import types
import pytest
from pathlib import Path
from datetime import datetime, timezone

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
    def emit_transfer(self, value, on):
        assert on == 'finalized'
        self.transfers.append((self.address, value))

class Provider:
    def __init__(self):
        self.body_by_url = {}
        self.answer = None
        self.validator_answer = None
    def render(self, url, mode='text'):
        return self.body_by_url[url]
    def exec_prompt(self, prompt, response_format='json'):
        assert response_format == 'json'
        return self.answer

class FakeVM:
    UserError = Revert
    Return = Return
    def __init__(self, provider):
        self.provider = provider
        self.disagree = False
    def run_nondet(self, leader, validator):
        result = leader()
        if self.disagree:
            raise RuntimeError('consensus mismatch')
        assert validator(Return(result)), 'validator rejected'
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
    monkeypatch.setitem(sys.modules, 'genlayer', gl)
    monkeypatch.setitem(sys.modules, 'genlayer.types', types_module)
    path = Path(__file__).resolve().parents[1] / 'contracts' / 'bermond.py'
    spec = importlib.util.spec_from_file_location('bermond_contract_under_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fake_time = {'now': 1_800_000_000}
    monkeypatch.setattr(mod, 'now_seconds', lambda: fake_time['now'])
    FakeRecipient.transfers = []
    return types.SimpleNamespace(mod=mod, gl=gl, provider=provider, vm=vm, time=fake_time, transfers=FakeRecipient.transfers)
