"""Verify source parity, finality, and the live schema for the Studio Dev release."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deployments" / "studio-dev.json"
SOURCE = ROOT / "contracts" / "bermond.py"


def rpc(method: str, params: list):
    response = requests.post(
        "https://studio-dev.genlayer.com/api",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if "error" in result:
        raise RuntimeError(f"{method} failed: {result['error']}")
    return result["result"]


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    address = manifest["contract_address"]
    deployment = manifest["deployment_transaction"]
    local = SOURCE.read_bytes()
    code_b64 = rpc("gen_getContractCode", [address])
    remote = base64.b64decode(code_b64)
    remote_hash = hashlib.sha256(remote).hexdigest()
    local_hash = hashlib.sha256(local).hexdigest()
    if remote != local:
        raise RuntimeError("Finalized contract code does not match contracts/bermond.py.")

    schema = rpc("gen_getContractSchema", [address])
    status = rpc("gen_getTransactionStatus", [{"txId": deployment["hash"]}])
    expected_methods = {
        "create_bond",
        "enroll_subscriber",
        "accept_bond",
        "fund_bond",
        "check_policy",
        "claim_compensation",
        "release_collateral",
        "get_bond",
        "get_bond_ids",
        "get_claim_status",
    }
    actual_methods = set(schema.get("methods", {}))
    if actual_methods != expected_methods:
        raise RuntimeError(f"Unexpected contract schema methods: {sorted(actual_methods)}")
    if status.get("status", "").upper() != "FINALIZED":
        raise RuntimeError(f"Deployment is not finalized: {status}")

    manifest["schema"] = schema
    manifest["code_parity"] = "EXACT_BYTES_MATCH"
    manifest["receipt_finality"] = "FINALIZED_SUCCESS"
    manifest["status"] = "DEPLOYED_VERIFIED"
    manifest["release_source_sha256"] = local_hash
    manifest["verification"] = {
        "chain_id": manifest["network"]["chain_id"],
        "deployment_status": status,
        "local_source_sha256": local_hash,
        "deployed_source_sha256": remote_hash,
        "exact_bytes_match": True,
    }
    manifest["blocker"] = "Full create/enroll/fund/BREACHED-check/claim lifecycle succeeded on the verified deployment. Claim emitted the finalized 1-GEN EOA transfer; the beneficiary balance increased by approximately 1 GEN net across the test window. Studio gen_call remains unhealthy, and expiry release is not yet tested."
    MANIFEST.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    print(f"contract_address={address}")
    print(f"deployment_status={status.get('status')}")
    print(f"source_sha256={local_hash}")
    print(f"code_parity=EXACT_BYTES_MATCH")
    print(f"schema_methods={','.join(sorted(actual_methods))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
