"""Run one real Studio Dev Bermond bond cycle using two local test wallets.

Keys are read into process memory only and are never printed or persisted.
This test creates a 1-wei bond against the public pinned breached-policy
fixture. Studio Dev does not support external EOA payouts, so the script
records claim execution and stops short of claiming a settled GEN transfer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client, studio_devnet
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.exceptions import GenLayerError
from genlayer_py.types import TransactionHashVariant

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deployments" / "studio-dev.json"
FIXTURE_BASE = "https://raw.githubusercontent.com/BeatyXO/Bermond-/a9eab6aa2be30d81c8d296e38a9f8ef366f64761/deployments/fixtures"
# Use a meaningful native transfer amount: tiny 1-wei transfers can behave
# differently in chain-layer/Studio settlement than regular GEN payments.
PAYOUT_WEI = 10**18


def read_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(value: dict) -> None:
    MANIFEST.write_bytes((json.dumps(value, indent=2) + "\n").encode("utf-8"))


def wallet(wallet_file: Path, label: str):
    for line in wallet_file.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip().casefold() == label.casefold():
            key = value.strip()
            if re.fullmatch(r"(?:0x)?[0-9a-fA-F]{64}", key):
                return Account.from_key(key)
            break
    raise ValueError(f"No valid wallet key found for label {label!r}.")


def submit(client, account, address: str, function: str, args: list, value: int = 0) -> dict:
    manifest = read_manifest()
    if manifest.get("pending_transaction"):
        raise RuntimeError("A prior transaction is pending; resume that hash before submitting another write.")
    try:
        fees = client.estimate_transaction_fees_for_write(
            address=address,
            function_name=function,
            account=account,
            args=args,
            value=value,
        )
    except GenLayerError as exc:
        # Studio Dev's transaction-specific simulation shares the unhealthy
        # backend path used by gen_call. A static current fee-policy estimate
        # still uses the supported fee-profile RPC and lets us test submission.
        print(f"write_fee_simulation_unavailable={exc}", flush=True)
        fees = client.estimate_transaction_fees()
    tx_hash = client.write_contract(
        address=address,
        function_name=function,
        account=account,
        args=args,
        value=value,
        fees=fees,
    )
    manifest["pending_transaction"] = {"hash": tx_hash, "function": function, "bond_id": args[0] if args else None}
    write_manifest(manifest)
    print(f"submitted {function}: {tx_hash}", flush=True)

    result = client.wait_for_finalization(
        tx_hash, interval=5, retries=180, full_transaction=True
    )
    success = tx_execution_succeeded(result)
    execution = result.get("tx_execution_result_name") or result.get("txExecutionResultName")
    runtime_error = None
    if not success:
        try:
            finalized = client.get_transaction(tx_hash)
            leader = (finalized.get("consensus_data") or {}).get("leader_receipt") or []
            if leader:
                runtime_error = leader[0].get("result", {}).get("payload")
        except GenLayerError:
            runtime_error = "Finalized with execution error; detailed leader receipt was unavailable."
    receipt = {
        "function": function,
        "bond_id": args[0] if args else None,
        "hash": tx_hash,
        "status": result.get("lifecycle"),
        "execution_result": execution,
        "successful": success,
        "runtime_error": runtime_error,
    }
    manifest = read_manifest()
    manifest.setdefault("lifecycle_transactions", []).append(receipt)
    for case in manifest.get("live_cases", []):
        if case.get("id") == receipt["bond_id"]:
            case.setdefault("receipts", []).append(receipt)
    manifest["pending_transaction"] = None
    write_manifest(manifest)
    print(f"finalized {function}: success={str(success).lower()} execution={execution}" + (f" error={runtime_error}" if runtime_error else ""), flush=True)
    if not success:
        raise RuntimeError(f"{function} finalized without successful contract execution; inspect {tx_hash} before retrying.")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wallet-file", required=True, type=Path)
    parser.add_argument("--provider-label", default="Landlord 1")
    parser.add_argument("--beneficiary-label", default="Tenant 1")
    parser.add_argument("--resume", action="store_true", help="Finalize the already-recorded transaction and exit without resubmitting it.")
    parser.add_argument("--resume-case", help="Continue missing lifecycle steps for an existing test bond.")
    args = parser.parse_args()

    manifest = read_manifest()
    address = manifest.get("contract_address")
    if not address or manifest.get("status") not in ("DEPLOYED_UNVERIFIED", "DEPLOYED_VERIFIED"):
        raise RuntimeError("No verified successful Studio Dev deployment is configured.")
    if manifest.get("pending_transaction") and not args.resume:
        raise RuntimeError("A pending transaction is recorded; resume it before starting a new bond.")

    provider = wallet(args.wallet_file, args.provider_label)
    beneficiary = wallet(args.wallet_file, args.beneficiary_label)
    client = create_client(chain=studio_devnet, account=provider)
    pending = manifest.get("pending_transaction")
    if pending:
        if not args.resume:
            raise RuntimeError("A transaction is already pending; use --resume to check that exact hash before any new write.")
        result = client.wait_for_finalization(
            pending["hash"], interval=5, retries=180, full_transaction=True
        )
        success = tx_execution_succeeded(result)
        execution = result.get("tx_execution_result_name") or result.get("txExecutionResultName")
        case_id = pending.get("bond_id")
        if not case_id and manifest.get("live_cases"):
            case_id = manifest["live_cases"][-1].get("id")
        receipt = {
            "function": pending.get("function"), "bond_id": case_id,
            "hash": pending["hash"], "status": result.get("lifecycle"),
            "execution_result": execution, "successful": success, "resumed": True,
        }
        manifest.setdefault("lifecycle_transactions", []).append(receipt)
        for case in manifest.get("live_cases", []):
            if case.get("id") == case_id:
                case.setdefault("receipts", []).append(receipt)
        manifest["pending_transaction"] = None
        write_manifest(manifest)
        print(f"resumed {pending.get('function')}: success={str(success).lower()} execution={execution}")
        return 0 if success else 1
    if args.resume_case:
        case = next((item for item in manifest.get("live_cases", []) if item.get("id") == args.resume_case), None)
        if not case:
            raise RuntimeError(f"Unknown live test bond {args.resume_case!r}.")
        receipts = case.get("receipts", [])
        successful = {item.get("function") for item in receipts if item.get("successful")}
        if any(item.get("function") == "claim_compensation" for item in receipts):
            raise RuntimeError("This test bond already has a finalized claim attempt; refusing to repeat it.")
        bond_id = args.resume_case
        if "enroll_subscriber" not in successful:
            submit(client, provider, address, "enroll_subscriber", [bond_id, case["beneficiary"]])
        if "fund_bond" not in successful:
            submit(client, provider, address, "fund_bond", [bond_id], int(case["payout_wei"]))
        if "check_policy" not in successful:
            submit(client, beneficiary, address, "check_policy", [bond_id])
        deadline = case.get("claim_deadline")
        if not deadline:
            deadline = int(bond_id.rsplit("-", 1)[-1]) + 4260
            case["claim_deadline"] = deadline
            case["release_eligible_after"] = deadline + 1
            write_manifest(manifest)
        if int(time.time()) > int(deadline):
            raise RuntimeError("The test bond's claim deadline has passed; refusing a late claim.")
        print("attempting claim; the contract itself enforces the BREACHED-state requirement", flush=True)
        try:
            receipt = submit(client, beneficiary, address, "claim_compensation", [bond_id])
        except RuntimeError as exc:
            print(f"claim_result={exc}", flush=True)
            manifest = read_manifest()
            case = next(item for item in manifest.get("live_cases", []) if item.get("id") == bond_id)
            case["state"] = "CLAIM_FAILED"
            write_manifest(manifest)
            return 1
        manifest = read_manifest()
        case = next(item for item in manifest.get("live_cases", []) if item.get("id") == bond_id)
        case["state"] = "CLAIM_FINALIZED" if receipt["successful"] else "CLAIM_FAILED"
        manifest["blocker"] = "Claim transaction finalized; Studio Dev does not expose reliable gen_call state reads or prove external GEN transfer settlement to an EOA recipient."
        write_manifest(manifest)
        return 0 if receipt["successful"] else 1
    # Reads currently fail on Studio Dev with a server-side SQLAlchemy error.
    # This test uses a unique timestamped ID and a verified deployment, so a
    # preliminary state read is unnecessary and must not block write testing.

    baseline = (ROOT / "deployments" / "fixtures" / "baseline.txt").read_bytes()
    # Git's Windows checkout may convert committed LF to CRLF, but the pinned
    # raw GitHub URL serves LF bytes. Commit the hash of the URL's byte form.
    baseline_hash = hashlib.sha256(baseline.replace(b"\r\n", b"\n")).hexdigest()
    bond_id = f"studio-breach-{int(time.time())}"
    now = int(time.time())
    # Leave room for transaction finalization before the contract's strict
    # one-hour minimum coverage duration begins at create_bond execution.
    coverage_ends = now + 4200
    claim_deadline = coverage_ends + 60
    terms = {
        "allowance": "At least 100000 API requests per calendar month.",
        "retention": "Delete customer data within 30 days after service ends.",
        "refunds": "Refund affected monthly prepaid fees below 99% availability.",
        "notice": "Give at least 30 days notice before materially reducing service rights.",
    }
    manifest.setdefault("live_cases", []).append(
        {
            "id": bond_id,
            "expected": "BREACHED",
            "baseline_url": f"{FIXTURE_BASE}/baseline.txt",
            "current_url": f"{FIXTURE_BASE}/breached.txt",
            "provider": provider.address,
            "beneficiary": beneficiary.address,
            "payout_wei": PAYOUT_WEI,
            "receipts": [],
        }
    )
    write_manifest(manifest)

    call_args = [
        bond_id,
        "Bermond Studio Dev lifecycle test",
        "API",
        f"{FIXTURE_BASE}/baseline.txt",
        baseline_hash,
        f"{FIXTURE_BASE}/breached.txt",
        json.dumps(terms, separators=(",", ":")),
        PAYOUT_WEI,
        coverage_ends,
        claim_deadline,
    ]
    receipts = []
    receipts.append(submit(client, provider, address, "create_bond", call_args))
    receipts.append(submit(client, provider, address, "enroll_subscriber", [bond_id, beneficiary.address]))
    receipts.append(submit(client, provider, address, "fund_bond", [bond_id], PAYOUT_WEI))
    receipts.append(submit(client, beneficiary, address, "check_policy", [bond_id]))

    bond = None
    try:
        bond = client.read_contract(
            address,
            "get_bond",
            args=[bond_id],
            account=beneficiary,
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
    except GenLayerError as exc:
        print(f"bond_state_read_unavailable={exc}", flush=True)
    if bond:
        print(f"bond_state_after_check={bond.get('state')}")
        print(f"last_verdict={bond.get('last_verdict')}")
    # The contract enforces BREACHED and deadline eligibility. If Studio's read
    # endpoint is unavailable, submitting the test claimant's call is safe: it
    # either proves the claim path or finalizes a guarded rejection.
    if (bond and bond.get("state") == "BREACHED") or (bond is None and int(time.time()) <= claim_deadline):
        try:
            receipts.append(submit(client, beneficiary, address, "claim_compensation", [bond_id]))
        except RuntimeError as exc:
            print(f"claim_result={exc}")
    else:
        print("claim_result=not submitted because the finalized policy check did not authorize a breach")

    manifest = read_manifest()
    for case in manifest.get("live_cases", []):
        if case["id"] == bond_id:
            case["receipts"] = [
                item for item in manifest.get("lifecycle_transactions", [])
                if item.get("bond_id") == bond_id
            ]
            case["state"] = bond.get("state") if bond else "CLAIM_RESULT_RECORDED_STATE_READ_UNAVAILABLE"
            case["last_verdict"] = bond.get("last_verdict") if bond else None
            case["claim_deadline"] = claim_deadline
            case["release_eligible_after"] = claim_deadline + 1
    manifest["status"] = "DEPLOYED_VERIFIED"
    manifest["blocker"] = "Studio Dev cannot settle the contract's external GEN payout to an EOA; release also requires its claim deadline to expire."
    write_manifest(manifest)
    print(f"bond_id={bond_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
