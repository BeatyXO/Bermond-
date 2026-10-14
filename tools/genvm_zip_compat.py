"""Compatibility adapter for GenVM releases that package SDK runners as ZIPs.

The pinned genvm-linter 0.11.0 and genlayer-test 0.29.2 only look for nested
TAR runners. Current GenVM bundles publish the same content as nested ZIPs.
This adapter extracts those ZIP members into each tool's documented cache
layout, then lets the tools' normal loaders and validators run unchanged.
"""
from __future__ import annotations

import os
import shutil
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable


def _runner_member(runner_type: str, runner_hash: str) -> str:
    return f"runners/{runner_type}/{runner_hash[:2]}/{runner_hash[2:]}.zip"


def _cached_bundle(cache: Path) -> Path | None:
    bundles = list(cache.glob("genvm-universal-*.tar.xz"))
    compatible = [path for path in bundles if "0.6.0" in path.name]
    if compatible:
        return sorted(compatible, reverse=True)[0]
    return sorted(bundles, reverse=True)[0] if bundles else None


def _safe_extract_zip(data, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(data) as bundle:
        for entry in bundle.infolist():
            name = PurePosixPath(entry.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError(f"Unsafe path in GenVM runner ZIP: {entry.filename!r}")
            target = (destination / Path(*name.parts)).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"Runner ZIP entry escapes extraction directory: {entry.filename!r}")
            # Runner packages contain regular files and directories only.
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"Symlink in GenVM runner ZIP is not allowed: {entry.filename!r}")
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(entry) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


def _extract_zip_member(archive: Path, runner_type: str, runner_hash: str, destination: Path) -> Path:
    member_name = _runner_member(runner_type, runner_hash)
    if (destination / "runner.json").is_file():
        return destination

    if destination.exists():
        shutil.rmtree(destination)
    requested = {member_name: destination}
    extracted_primary = False
    with tarfile.open(archive, "r|xz") as outer:
        for member in outer:
            target = requested.get(member.name)
            if target is None:
                continue
            stream = outer.extractfile(member)
            if stream is None:
                raise RuntimeError(f"Could not read GenVM runner bundle member {member.name}")
            _safe_extract_zip(stream, target)
            requested.pop(member.name, None)
            if member.name == member_name:
                extracted_primary = True
                # Runner manifests identify the exact SDK libraries the
                # Python runner depends on. Extract them during the same XZ
                # stream pass so each large release bundle is decompressed once.
                manifest_path = target / "runner.json"
                if manifest_path.is_file():
                    import json

                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    deps = {}
                    for item in manifest.get("Seq", []):
                        dep = item.get("Depends") if isinstance(item, dict) else None
                        if isinstance(dep, str) and ":" in dep:
                            dep_type, dep_hash = dep.rsplit(":", 1)
                            if dep_type.startswith("py-lib-"):
                                deps[_runner_member(dep_type, dep_hash)] = target.parent.parent / dep_type / dep_hash
                    requested.update(deps)
            if not requested:
                break
    if not (destination / "runner.json").is_file():
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError(f"GenVM runner {runner_type}:{runner_hash} has no runner.json")
    if not extracted_primary:
        raise FileNotFoundError(f"GenVM bundle has no runner {runner_type}:{runner_hash}")
    return destination


def _install_for_linter() -> None:
    from genvm_linter.validate import artifacts, sdk_loader
    from genvm_linter.validate import validator

    original_cache = artifacts.CACHE_DIR
    project_cache = Path(__file__).resolve().parents[1] / ".cache" / "genvm-linter"
    original_resolve = artifacts.resolve_version
    original_download = artifacts.download_artifacts
    artifacts.CACHE_DIR = project_cache

    def resolve_version() -> str:
        pinned = os.environ.get("GENVM_VERSION")
        if pinned:
            return pinned
        cached = artifacts.list_cached_versions()
        if cached:
            return cached[0]
        bundle = _cached_bundle(original_cache)
        if bundle:
            return bundle.name.removeprefix("genvm-universal-").removesuffix(".tar.xz")
        return original_resolve()

    def download_artifacts(version: str | None = None, progress_callback=None) -> Path:
        version = version or resolve_version()
        cached_path = original_cache / f"genvm-universal-{version}.tar.xz"
        if cached_path.is_file():
            return cached_path
        return original_download(version, progress_callback)

    artifacts.resolve_version = resolve_version
    artifacts.download_artifacts = download_artifacts
    sdk_loader.download_artifacts = download_artifacts
    original: Callable = artifacts.extract_runner

    def extract(archive: Path, runner_type: str, runner_hash: str) -> Path:
        target = artifacts.get_cache_dir() / "extracted" / archive.stem.removeprefix("genvm-universal-") / runner_type / runner_hash
        if (target / "runner.json").is_file():
            return target
        direct_cache = Path(__file__).resolve().parents[1] / ".cache" / "gltest-direct" / "extracted" / "v0.6.0-rc5" / runner_type / runner_hash
        if (direct_cache / "runner.json").is_file():
            return direct_cache
        try:
            return _extract_zip_member(archive, runner_type, runner_hash, target)
        except FileNotFoundError:
            return original(archive, runner_type, runner_hash)

    artifacts.extract_runner = extract
    sdk_loader.extract_runner = extract

    original_setup_wasi = sdk_loader.setup_wasi_mocks

    def setup_wasi_mocks() -> None:
        original_setup_wasi()
        import sys

        # Keep GenLayer's runtime-only message decoder disabled during schema
        # reflection; the linter is importing types, not executing a VM call.
        sys.modules["_genlayer_wasi"].FAKE_VM = True

    sdk_loader.setup_wasi_mocks = setup_wasi_mocks

    original_load_sdk: Callable = sdk_loader.load_sdk

    def load_sdk(contract_path: Path, progress_callback=None):
        try:
            return original_load_sdk(contract_path, progress_callback)
        except ModuleNotFoundError as exc:
            if exc.name != "genlayer.py":
                raise
            from genlayer._internal.get_schema import get_schema

            return get_schema, []

    sdk_loader.load_sdk = load_sdk
    validator.load_sdk = load_sdk


def _install_for_direct_mode() -> None:
    from gltest.direct import sdk_loader
    from gltest.direct import loader as direct_loader
    from gltest.direct.vm import VMContext
    from gltest.direct import wasi_mock

    original_cache = sdk_loader.CACHE_DIR
    project_cache = Path(__file__).resolve().parents[1] / ".cache" / "gltest-direct"
    original_get_latest = sdk_loader.get_latest_version
    original_download = sdk_loader.download_artifacts
    sdk_loader.CACHE_DIR = project_cache

    def get_latest_version() -> str:
        pinned = os.environ.get("GENVM_VERSION")
        if pinned:
            return pinned
        bundle = _cached_bundle(original_cache)
        if bundle:
            return bundle.name.removeprefix("genvm-universal-").removesuffix(".tar.xz")
        return original_get_latest()

    def download_artifacts(version: str) -> Path:
        cached_path = original_cache / f"genvm-universal-{version}.tar.xz"
        if cached_path.is_file():
            return cached_path
        return original_download(version)

    sdk_loader.get_latest_version = get_latest_version
    sdk_loader.download_artifacts = download_artifacts
    original: Callable = sdk_loader.extract_runner

    def gl_call_v06(data: bytes, /) -> int:
        """Decode and encode host calls with the current SDK's calldata API."""
        import io

        from genlayer import calldata

        vm = wasi_mock.get_vm()
        try:
            request = calldata.decode(data)
        except Exception as exc:
            vm._trace(f"gl_call decode error: {exc}")
            return 2**32 - 1
        if getattr(vm, "_in_nondet", False) and isinstance(request, dict):
            for operation in ("DeployContract", "CallContract", "PostMessage"):
                if operation in request:
                    raise RuntimeError(f"Cross-contract call ({operation}) is forbidden inside run_nondet")
        response = wasi_mock._handle_gl_call(vm, request)
        if response is None:
            return 2**32 - 1
        if (
            isinstance(request, dict)
            and isinstance(request.get("ExecPrompt"), dict)
            and request["ExecPrompt"].get("response_format") == "json"
            and isinstance(response, dict)
            and isinstance(response.get("ok"), (dict, list))
        ):
            import json

            response["ok"] = json.dumps(response["ok"], separators=(",", ":"))
        encoded = response if isinstance(response, bytes) else calldata.encode(response)
        fd_counter = getattr(wasi_mock._local, "fd_counter", 100)
        wasi_mock._local.fd_counter = fd_counter + 1
        wasi_mock._local.fd_buffers[fd_counter] = io.BytesIO(encoded)
        return fd_counter

    wasi_mock.gl_call = gl_call_v06

    def refresh_gl_message(vm) -> None:
        """Keep the v0.6 SDK's message module in sync with Direct Mode state."""
        import sys

        module = sys.modules.get("genlayer.message")
        if module is None:
            return
        from genlayer.types import Address

        def address(value):
            if value is None or isinstance(value, Address):
                return value
            if isinstance(value, bytes):
                return Address(value)
            if hasattr(value, "as_bytes"):
                return Address(value.as_bytes)
            return Address(value)

        raw = vm.get_message_raw()
        raw["contract_address"] = address(raw["contract_address"])
        raw["sender_address"] = address(raw["sender_address"])
        raw["origin_address"] = address(raw["origin_address"])
        raw["signer_address"] = raw["sender_address"]
        module.raw = raw
        for key, value in raw.items():
            setattr(module, key, value)

    VMContext._refresh_gl_message = refresh_gl_message
    original_cleanup: Callable = VMContext._cleanup_after_deactivate

    def cleanup_after_deactivate(vm) -> None:
        try:
            original_cleanup(vm)
        finally:
            path = getattr(vm, "_direct_message_path", None)
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
                vm._direct_message_path = None

    VMContext._cleanup_after_deactivate = cleanup_after_deactivate

    def inject_message(vm) -> None:
        """Bridge genlayer-test 0.29's legacy loader to the v0.6 SDK API."""
        import os
        import tempfile

        from genlayer import calldata
        from genlayer.types import Address

        def address(value):
            return Address(value) if isinstance(value, bytes) else value

        message_data = {
            "contract_address": address(vm._contract_address),
            "sender_address": address(vm.sender),
            "origin_address": address(vm.origin),
            "stack": [],
            "value": vm._value,
            "datetime": vm._datetime,
            "is_init": False,
            "chain_id": vm._chain_id,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
        }
        encoded = calldata.encode(message_data)
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, encoded)
            os.lseek(fd, 0, os.SEEK_SET)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(fd, 0)
        finally:
            os.close(fd)
            try:
                os.unlink(path)
            except PermissionError:
                # Windows keeps fd 0's file handle open until VM cleanup.
                vm._direct_message_path = path

    direct_loader._inject_message_to_fd0 = inject_message

    original_allocate: Callable = direct_loader._allocate_contract

    def allocate_contract(contract_cls, vm, *args, **kwargs):
        try:
            from genlayer.storage import inmem_allocate
        except ImportError:
            return original_allocate(contract_cls, vm, *args, **kwargs)
        return inmem_allocate(contract_cls, *args, **kwargs)

    direct_loader._allocate_contract = allocate_contract

    original_patch_run_nondet: Callable = direct_loader._patch_run_nondet_for_direct_mode
    sentinel = object()

    def patch_run_nondet_v06() -> None:
        original_patch_run_nondet()
        import genlayer.vm as gl_vm

        def run_nondet(leader_fn, validator_fn, /, **kwargs):
            vm = wasi_mock.get_vm()
            if vm._check_pickling:
                direct_loader._validate_pickling(leader_fn, "leader_fn")
                direct_loader._validate_pickling(validator_fn, "validator_fn")
            vm._in_nondet = True
            try:
                result = leader_fn()
            except Exception as exc:
                vm._trace(f"direct run_nondet leader error: {type(exc).__name__}: {exc}")
                raise
            finally:
                vm._in_nondet = False
            vm._captured_validators.append((result, leader_fn, validator_fn))
            return result

        gl_vm.run_nondet = run_nondet
        gl_vm._direct_mode_patched = True

    direct_loader._patch_run_nondet_for_direct_mode = patch_run_nondet_v06

    def run_validator(vm, leader_result=sentinel, leader_error=None, index=-1):
        if not vm._captured_validators:
            raise RuntimeError("No validator captured by Direct Mode run_nondet")
        stored_result, _leader_fn, validator_fn = vm._captured_validators[index]
        import genlayer.vm as gl_vm

        if leader_error is not None:
            wrapped = gl_vm.UserError(leader_error)
        elif leader_result is sentinel:
            wrapped = gl_vm.Return(calldata=stored_result)
        else:
            wrapped = gl_vm.Return(calldata=leader_result)
        vm._in_nondet = True
        try:
            return validator_fn(wrapped)
        finally:
            vm._in_nondet = False

    VMContext.run_validator = run_validator

    def extract(archive: Path, runner_type: str, runner_hash: str | None = None, version: str | None = None) -> Path:
        if version is None:
            version = archive.stem.removeprefix("genvm-universal-")
        if not runner_hash or runner_hash.lower() == "latest":
            return original(archive, runner_type, runner_hash, version)
        target = sdk_loader.CACHE_DIR / "extracted" / version / runner_type / runner_hash
        if (target / "runner.json").is_file():
            return target
        try:
            return _extract_zip_member(archive, runner_type, runner_hash, target)
        except FileNotFoundError:
            return original(archive, runner_type, runner_hash, version)

    sdk_loader.extract_runner = extract


def install() -> None:
    """Patch installed tools in this process only; no package files are changed."""
    _install_for_linter()
    _install_for_direct_mode()


def lint_cli() -> None:
    """Run genvm-lint with ZIP runner compatibility enabled."""
    install()
    from genvm_linter.cli import cli

    cli()


if __name__ == "__main__":
    lint_cli()
