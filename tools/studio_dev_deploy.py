"""Deploy Bermond to GenLayer Studio Dev without persisting wallet secrets.

The selected private key is read from a local test-wallet file into memory and
is never printed or written by this script. Use only Studio Dev test wallets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client, studio_devnet
from genlayer_py.assertions import tx_execution_succeeded

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "bermond.py"
MANIFEST = ROOT / "deployments" / "studio-dev.json"


def wallet_key(wallet_file: Path, label: str):
    text = wallet_file.read_text(encoding="utf-8")
    for line in text.splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip().casefold() == label.casefold():
            key = value.strip()
            if re.fullmatch(r"(?:0x)?[0-9a-fA-F]{64}", key):
                return Account.from_key(key)
            break
    raise ValueError(f"No valid wallet key found for label {label!r}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wallet-file", required=True, type=Path)
    parser.add_argument("--provider-label", default="Landlord 1")
    parser.add_argument("--resume", action="store_true", help="Finalize the hash already recorded in the manifest; do not deploy again.")
    args = parser.parse_args()

    account = wallet_key(args.wallet_file, args.provider_label)
    source = CONTRACT.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    client = create_client(chain=studio_devnet, account=account)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pending = manifest.get("pending_deployment")
    if pending:
        if not args.resume:
            raise RuntimeError("A deployment hash is already pending; use --resume to check that exact hash before submitting anything else.")
        tx_hash = pending["hash"]
        source_hash = pending["source_sha256"]
    else:
        if args.resume:
            raise RuntimeError("There is no pending deployment hash to resume.")
        # Obtain the live v0.6 fee profile. Do not override its execution budget:
        # Studio Dev enforces the current runtime floor at submission.
        fees = client.estimate_transaction_fees()
        tx_hash = client.deploy_contract(code=source, account=account, fees=fees)
        manifest["pending_deployment"] = {"hash": tx_hash, "source_sha256": source_hash}
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"transaction_hash={tx_hash}", flush=True)
    receipt = client.wait_for_finalization(
        tx_hash, interval=5, retries=180, full_transaction=True
    )
    successful = tx_execution_succeeded(receipt)
    execution_result = (
        receipt.get("tx_execution_result_name")
        or receipt.get("txExecutionResultName")
    )
    contract_address = receipt.get("contract_address") or receipt.get("recipient")
    if not contract_address and isinstance(receipt.get("tx_data_decoded"), dict):
        contract_address = receipt["tx_data_decoded"].get("contract_address")

    attempts = manifest.get("deployment_attempts", [])
    attempts.append(
        {
            "hash": tx_hash,
            "status": receipt.get("status") or receipt.get("lifecycle"),
            "execution_result": execution_result,
            "contract_address": contract_address if successful else None,
            "attempted_address": contract_address if not successful else None,
            "source_sha256": source_hash,
        }
    )
    manifest["deployment_attempts"] = attempts
    manifest["last_deployment_attempt"] = {
        "hash": tx_hash,
        "status": receipt.get("status") or receipt.get("lifecycle"),
        "execution_result": execution_result,
        "contract_address": contract_address if successful else None,
        "attempted_address": contract_address if not successful else None,
        "source_sha256": source_hash,
    }
    manifest["pending_deployment"] = None
    if successful and contract_address:
        manifest["release_source_sha256"] = source_hash
        manifest["deployment_transaction"] = manifest["last_deployment_attempt"]
        manifest["contract_address"] = contract_address
        manifest["status"] = "DEPLOYED_UNVERIFIED"
        manifest["receipt_finality"] = "FINALIZED_SUCCESS"
        manifest["code_parity"] = "UNVERIFIED"
        manifest["blocker"] = "Deployment finalized successfully; verify contract code and schema before use."
    elif not manifest.get("contract_address"):
        manifest["status"] = "PENDING_NO_DEPLOYMENT"
        manifest["receipt_finality"] = "FINALIZED_FAILED"
        manifest["blocker"] = "Deployment finalized with contract execution failure; inspect last_deployment_attempt before retrying."
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"source_sha256={source_hash}")
    print(f"finalized_success={str(successful).lower()}")
    print(f"execution_result={execution_result}")
    print(f"contract_address={contract_address or 'none'}")
    return 0 if successful and contract_address else 1


if __name__ == "__main__":
    raise SystemExit(main())
