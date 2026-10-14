"""Prepare the official GenVM runner archives for genlayer-test Direct Mode.

The official linter extracts the selected runner packages, while Direct Mode
accepts those same packages through its documented GENVM_PREBUILT_DIR setting.
This bridges their filesystem layouts without monkeypatching either tool.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "bermond.py"


def _archive_runner(source: Path, root: Path, runner_type: str, runner_hash: str) -> None:
    destination = root / "runners" / runner_type / runner_hash[:2] / f"{runner_hash[2:]}.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(source)
                if ".." in relative.parts:
                    raise ValueError(f"invalid runner path: {relative}")
                archive.write(path, relative.as_posix())


def prepare(contract: Path = CONTRACT) -> Path:
    # These are the actual artifact download/extract functions used by the
    # installed GenVM linter; do not invent runner locations or version hashes.
    from genvm_linter.validate import artifacts
    from gltest.direct.sdk_loader import parse_contract_header

    version = os.environ.get("GENVM_VERSION")
    if not version:
        version = artifacts.resolve_version()
    bundle = artifacts.download_artifacts(version)
    contract_deps = parse_contract_header(contract)
    runner_hash = contract_deps.get("py-genlayer")
    if not runner_hash:
        raise RuntimeError(f"No py-genlayer dependency found in {contract}")
    runner_source = artifacts.extract_runner(bundle, "py-genlayer", runner_hash)
    if not (runner_source / "runner.json").is_file():
        raise FileNotFoundError(f"Official runner py-genlayer:{runner_hash} has no runner.json")
    runner_manifest = json.loads((runner_source / "runner.json").read_text(encoding="utf-8"))
    runtime_deps: dict[str, str] = {}
    for item in runner_manifest.get("Seq", []):
        dependency = item.get("Depends") if isinstance(item, dict) else None
        if isinstance(dependency, str) and ":" in dependency:
            name, digest = dependency.split(":", 1)
            runtime_deps[name] = digest

    selected: list[tuple[str, str, Path]] = [("py-genlayer", runner_hash, runner_source)]
    for runner_type in ("py-lib-genlayer-std", "py-lib-genlayer-embeddings", "py-lib-protobuf"):
        digest = contract_deps.get(runner_type) or runtime_deps.get(runner_type)
        if digest:
            source = artifacts.extract_runner(bundle, runner_type, digest)
            selected.append((runner_type, digest, source))
            if runner_type == "py-lib-genlayer-embeddings":
                embeddings_manifest = json.loads((source / "runner.json").read_text(encoding="utf-8"))
                for item in embeddings_manifest.get("Seq", []):
                    dependency = item.get("Depends") if isinstance(item, dict) else None
                    if isinstance(dependency, str) and dependency.startswith("py-lib-protobuf:"):
                        _, proto_hash = dependency.split(":", 1)
                        if "py-lib-protobuf" not in {name for name, _, _ in selected}:
                            proto_source = artifacts.extract_runner(bundle, "py-lib-protobuf", proto_hash)
                            selected.append(("py-lib-protobuf", proto_hash, proto_source))
                        break

    if not selected:
        raise RuntimeError(f"No GenVM runner dependencies found in {contract}")
    cache_root = ROOT / ".cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=f"genvm-prebuilt-{version}-", dir=cache_root))
    for runner_type, runner_hash, source in selected:
        _archive_runner(source, output, runner_type, runner_hash)
    return output


if __name__ == "__main__":
    try:
        path = prepare()
    except Exception as exc:
        print(f"Could not prepare the official GenVM runner bundle: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(path)
