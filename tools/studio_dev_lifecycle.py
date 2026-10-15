"""Run one real Studio Dev Bermond bond cycle using two local test wallets.

Keys are read into process memory only and are never printed or persisted.
This test creates a small 1-GEN bond against the pinned public policy fixture.
It records finalized receipts and never falls back to guessed fees if the
network cannot estimate the requested transaction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client, studio_devnet
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.exceptions import GenLayerError
from genlayer_py.types import TransactionHashVariant
from tx_status import accepted_finalized_execution

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deployments" / "studio-dev.json"
CONTRACT = ROOT / "contracts" / "bermond.py"
FIXTURE_BASE = "https://raw.githubusercontent.com/BeatyXO/Bermond-/a9eab6aa2be30d81c8d296e38a9f8ef366f64761/deployments/fixtures"
# Use a meaningful native transfer amount: tiny 1-wei transfers can behave
# differently in chain-layer/Studio settlement than regular GEN payments.
PAYOUT_WEI = 10**18
FINALIZATION_POLL_INTERVAL_MS = 5_000
FINALIZATION_RETRIES = 180


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
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
            # Studio's default simulation date can differ from the current
            # network date; pin it to UTC so time-bound calls simulate the
            # same validity window they will have when submitted.
            sim_config={
                "genvm_datetime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            },
        )
    except GenLayerError as exc:
        manifest = read_manifest()
        for case in manifest.get("live_cases", []):
            if args and case.get("id") == args[0]:
                case["state"] = "PREFLIGHT_FEE_ESTIMATE_FAILED"
                case["preflight_error"] = str(exc)[:500]
        write_manifest(manifest)
        raise
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
        tx_hash,
        interval=FINALIZATION_POLL_INTERVAL_MS,
        retries=FINALIZATION_RETRIES,
        full_transaction=True,
    )
    leader_execution_succeeded = tx_execution_succeeded(result)
    lifecycle = result.get("lifecycle") or {}
    success = accepted_finalized_execution(result, leader_execution_succeeded)
    execution = result.get("tx_execution_result_name") or result.get("txExecutionResultName")
    runtime_error = None
    if not success:
        if leader_execution_succeeded and str(lifecycle.get("state", "")).casefold() == "finalized":
            runtime_error = "Leader execution succeeded, but consensus outcome was not accepted: " + str(lifecycle.get("outcome", "unknown"))
        else:
            try:
                finalized = client.get_transaction(tx_hash)
                leader = (finalized.get("consensus_data") or {}).get("leader_receipt") or []
                if leader:
                    runtime_error = leader[0].get("result", {}).get("payload")
            except GenLayerError:
                runtime_error = "No accepted finalized execution; detailed leader receipt was unavailable."
    receipt = {
        "function": function,
        "bond_id": args[0] if args else None,
        "hash": tx_hash,
        "status": result.get("lifecycle"),
        "execution_result": execution,
        "successful": success,
        "leader_execution_succeeded": leader_execution_succeeded,
        "lifecycle_state": lifecycle.get("state"),
        "consensus_outcome": lifecycle.get("outcome"),
        "result_name": result.get("result_name") or result.get("resultName"),
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
    parser.add_argument("--release-test", action="store_true", help="Create and fund an ACTIVE 1-GEN bond for expiry-release testing.")
    parser.add_argument("--release-case", help="Release an existing expiry-test bond after its claim deadline.")
    args = parser.parse_args()

    manifest = read_manifest()
    address = manifest.get("contract_address")
    if not address or manifest.get("status") not in ("DEPLOYED_UNVERIFIED", "DEPLOYED_VERIFIED"):
        raise RuntimeError("No verified successful Studio Dev deployment is configured.")
    working_source_hash = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    if working_source_hash != manifest.get("release_source_sha256"):
        raise RuntimeError(
            "The current contract source does not match the recorded deployment. "
            "Refusing lifecycle writes to an older Studio Dev schema. Deploy and verify the candidate first."
        )
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
            pending["hash"],
            interval=FINALIZATION_POLL_INTERVAL_MS,
            retries=FINALIZATION_RETRIES,
            full_transaction=True,
        )
        leader_execution_succeeded = tx_execution_succeeded(result)
        lifecycle = result.get("lifecycle") or {}
        success = accepted_finalized_execution(result, leader_execution_succeeded)
        execution = result.get("tx_execution_result_name") or result.get("txExecutionResultName")
        case_id = pending.get("bond_id")
        if not case_id and manifest.get("live_cases"):
            case_id = manifest["live_cases"][-1].get("id")
        receipt = {
            "function": pending.get("function"), "bond_id": case_id,
            "hash": pending["hash"], "status": result.get("lifecycle"),
            "execution_result": execution, "successful": success, "resumed": True,
            "leader_execution_succeeded": leader_execution_succeeded,
            "lifecycle_state": lifecycle.get("state"),
            "consensus_outcome": lifecycle.get("outcome"),
            "result_name": result.get("result_name") or result.get("resultName"),
        }
        manifest.setdefault("lifecycle_transactions", []).append(receipt)
        for case in manifest.get("live_cases", []):
            if case.get("id") == case_id:
                case.setdefault("receipts", []).append(receipt)
        manifest["pending_transaction"] = None
        write_manifest(manifest)
        print(f"resumed {pending.get('function')}: success={str(success).lower()} execution={execution}")
        return 0 if success else 1
    if args.release_case:
        case = next((item for item in manifest.get("live_cases", []) if item.get("id") == args.release_case), None)
        if not case:
            raise RuntimeError(f"Unknown live release test bond {args.release_case!r}.")
        if str(case.get("state", "")).startswith("RELEASE_FINALIZED"):
            raise RuntimeError("This release test already finalized; refusing a duplicate release.")
        prior_release_attempts = [
            item for item in manifest.get("lifecycle_transactions", [])
            if item.get("bond_id") == args.release_case and item.get("function") == "release_collateral"
        ]
        if prior_release_attempts:
            raise RuntimeError("A release transaction was already submitted for this bond; inspect its receipt and finalized state before any manual recovery. Refusing a blind retry.")
        deadline = int(case["claim_deadline"])
        if int(time.time()) <= deadline:
            raise RuntimeError(f"Claim deadline has not passed; release eligible after {deadline} UTC.")
        before_state = client.read_contract(
            address,
            "get_bond",
            args=[args.release_case],
            account=provider,
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        if before_state.get("state") not in ("ACTIVE", "UNRESOLVED", "BREACHED"):
            raise RuntimeError("Finalized bond state is not releasable; no release submitted.")
        if int(before_state.get("claim_deadline", -1)) != deadline:
            raise RuntimeError("Manifest deadline does not match finalized bond state; no release submitted.")
        expected_remaining = int(before_state.get("reserved_wei", 0))
        provider_balance_before = None
        provider_balance_after = None
        try:
            provider_balance_before = int(client.get_balance(provider.address, block_identifier="finalized"))
        except GenLayerError as exc:
            print(f"provider_balance_before_release_unavailable={exc}", flush=True)
        receipt = submit(client, provider, address, "release_collateral", [args.release_case])
        try:
            after_state = client.read_contract(
                address,
                "get_bond",
                args=[args.release_case],
                account=provider,
                transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
            )
        except GenLayerError as exc:
            after_state = None
            print(f"post_release_state_read_unavailable={exc}", flush=True)
        try:
            provider_balance_after = int(client.get_balance(provider.address, block_identifier="finalized"))
        except GenLayerError as exc:
            print(f"provider_balance_after_release_unavailable={exc}", flush=True)
        manifest = read_manifest()
        case = next(item for item in manifest.get("live_cases", []) if item.get("id") == args.release_case)
        balance_delta = (
            provider_balance_after - provider_balance_before
            if provider_balance_before is not None and provider_balance_after is not None
            else None
        )
        state_verified = (
            after_state is not None
            and after_state.get("state") == "CLOSED"
            and int(after_state.get("reserved_wei", -1)) == 0
            and int(after_state.get("pending_wei", -1)) >= expected_remaining
        )
        balance_delta_observed = expected_remaining == 0 or (balance_delta is not None and balance_delta > 0)
        case["state"] = (
            "RELEASE_FINALIZED_ACCOUNTING_PENDING"
            if receipt["successful"] and state_verified and balance_delta_observed
            else "RELEASE_FINALIZED_EVIDENCE_INCOMPLETE"
            if receipt["successful"]
            else "RELEASE_FAILED"
        )
        case["release_receipt"] = receipt
        case["post_release_state"] = (
            {
                "state": after_state.get("state"),
                "reserved_wei": after_state.get("reserved_wei"),
                "released_wei": after_state.get("released_wei"),
                "pending_wei": after_state.get("pending_wei"),
            }
            if after_state is not None
            else None
        )
        case["provider_balance_before_release_wei"] = provider_balance_before
        case["provider_balance_after_release_wei"] = provider_balance_after
        case["provider_balance_delta_wei"] = balance_delta
        manifest["blocker"] = (
            "Expiry release transaction finalized; inspect post-release bond state and provider balance delta. "
            "The contract still accounts for the emitted transfer as pending until settlement reconciliation is available."
        )
        write_manifest(manifest)
        return 0 if receipt["successful"] and state_verified and balance_delta_observed else 1
    if args.resume_case:
        case = next((item for item in manifest.get("live_cases", []) if item.get("id") == args.resume_case), None)
        if not case:
            raise RuntimeError(f"Unknown live test bond {args.resume_case!r}.")
        receipts = case.get("receipts", [])
        successful = {item.get("function") for item in receipts if item.get("successful")}
        prior_checks = [item for item in receipts if item.get("function") == "check_policy"]
        if prior_checks and not prior_checks[-1].get("successful"):
            raise RuntimeError(
                "A prior check_policy attempt did not reach accepted consensus; "
                "refusing to retry it on the same case. Review the finalized outcome first."
            )
        if any(item.get("function") == "claim_compensation" for item in receipts):
            raise RuntimeError("This test bond already has a finalized claim attempt; refusing to repeat it.")
        bond_id = args.resume_case
        if "enroll_subscriber" not in successful:
            submit(client, provider, address, "enroll_subscriber", [bond_id, case["beneficiary"]])
        if "accept_bond" not in successful:
            fingerprint = case.get("policy_fingerprint")
            if not fingerprint:
                raise RuntimeError("The committed policy fingerprint is missing; refusing to fund an unverifiable beneficiary acceptance.")
            submit(client, beneficiary, address, "accept_bond", [bond_id, fingerprint])
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
        try:
            pre_claim_bond = client.read_contract(
                address,
                "get_bond",
                args=[bond_id],
                account=beneficiary,
                transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
            )
        except GenLayerError as exc:
            manifest = read_manifest()
            case = next(item for item in manifest.get("live_cases", []) if item.get("id") == bond_id)
            case["state"] = "CLAIM_STATE_READ_UNAVAILABLE"
            case["claim_submitted"] = False
            case["pre_claim_state_error"] = str(exc)[:500]
            manifest["blocker"] = "Finalized bond state was unavailable before claim; no claim was submitted."
            write_manifest(manifest)
            return 1
        if (
            pre_claim_bond.get("state") != "BREACHED"
            or int(pre_claim_bond.get("checks", 0)) < 1
            or int(pre_claim_bond.get("claim_deadline", -1)) != int(deadline)
        ):
            manifest = read_manifest()
            case = next(item for item in manifest.get("live_cases", []) if item.get("id") == bond_id)
            case["state"] = "CLAIM_WITHHELD_FINALIZED_STATE"
            case["claim_submitted"] = False
            case["pre_claim_state"] = {
                "state": pre_claim_bond.get("state"),
                "checks": pre_claim_bond.get("checks"),
                "claim_deadline": pre_claim_bond.get("claim_deadline"),
            }
            manifest["blocker"] = "Finalized bond state did not authorize a claim; the lifecycle runner withheld it."
            write_manifest(manifest)
            return 1
        print("finalized state confirms breach; submitting one claim", flush=True)
        balance_before_claim = None
        try:
            balance_before_claim = int(client.get_balance(beneficiary.address, block_identifier="finalized"))
        except GenLayerError as exc:
            print(f"beneficiary_balance_before_claim_unavailable={exc}", flush=True)
        try:
            receipt = submit(client, beneficiary, address, "claim_compensation", [bond_id])
        except RuntimeError as exc:
            print(f"claim_result={exc}", flush=True)
            manifest = read_manifest()
            case = next(item for item in manifest.get("live_cases", []) if item.get("id") == bond_id)
            case["state"] = "CLAIM_FAILED"
            write_manifest(manifest)
            return 1
        post_claim_bond = None
        balance_after_claim = None
        try:
            post_claim_bond = client.read_contract(
                address,
                "get_bond",
                args=[bond_id],
                account=beneficiary,
                transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
            )
        except GenLayerError as exc:
            print(f"post_claim_state_read_unavailable={exc}", flush=True)
        try:
            balance_after_claim = int(client.get_balance(beneficiary.address, block_identifier="finalized"))
        except GenLayerError as exc:
            print(f"beneficiary_balance_after_claim_unavailable={exc}", flush=True)
        balance_delta = (
            balance_after_claim - balance_before_claim
            if balance_before_claim is not None and balance_after_claim is not None
            else None
        )
        claimed = post_claim_bond is not None and beneficiary.address.lower() in post_claim_bond.get("claimed", [])
        verified = receipt["successful"] and claimed and balance_delta is not None and balance_delta > 0
        manifest = read_manifest()
        case = next(item for item in manifest.get("live_cases", []) if item.get("id") == bond_id)
        case["state"] = "CLAIM_FINALIZED_ACCOUNTING_PENDING" if verified else "CLAIM_FINALIZED_EVIDENCE_INCOMPLETE"
        case["post_claim_state"] = (
            {
                "state": post_claim_bond.get("state"),
                "claimed": claimed,
                "pending_wei": post_claim_bond.get("pending_wei"),
                "paid_wei": post_claim_bond.get("paid_wei"),
                "reserved_wei": post_claim_bond.get("reserved_wei"),
            }
            if post_claim_bond is not None
            else None
        )
        case["beneficiary_balance_before_claim_wei"] = balance_before_claim
        case["beneficiary_balance_after_claim_wei"] = balance_after_claim
        case["beneficiary_balance_delta_wei"] = balance_delta
        manifest["blocker"] = "Claim transaction finalized; inspect the post-claim state and beneficiary balance delta. Contract accounting retains emitted EOA transfers as pending until settlement is independently reconciled."
        write_manifest(manifest)
        return 0 if verified else 1
    # The live deployment's code and schema have already been verified. Never
    # submit a claim unless a finalized read confirms the recorded breach.

    baseline = (ROOT / "deployments" / "fixtures" / "baseline.txt").read_bytes()
    # Git's Windows checkout may convert committed LF to CRLF, but the pinned
    # raw GitHub URL serves LF bytes. Commit the hash of the URL's byte form.
    baseline_hash = hashlib.sha256(baseline.replace(b"\r\n", b"\n")).hexdigest()
    bond_id = f"studio-release-{int(time.time())}" if args.release_test else f"studio-breach-{int(time.time())}"
    now = int(time.time())
    # Leave room for transaction finalization before the contract's strict
    # one-hour minimum coverage duration begins at create_bond execution.
    coverage_ends = now + (3700 if args.release_test else 4200)
    claim_deadline = coverage_ends + (1 if args.release_test else 60)
    terms = {
        "allowance": "At least 100000 API requests per calendar month.",
        "retention": "Delete customer data within 30 days after service ends.",
        "refunds": "Refund affected monthly prepaid fees below 99% availability.",
        "notice": "Give at least 30 days notice before materially reducing service rights.",
    }
    baseline_identity = {
        "document_id": "bermond-fixture-baseline-v1",
        "publisher": "Bermond Studio Dev test fixture",
        "version": "fixture-v1",
    }
    policy_payload = [
        provider.address.lower(), bond_id, baseline_identity,
        f"{FIXTURE_BASE}/baseline.txt", baseline_hash,
        f"{FIXTURE_BASE}/breached.txt", terms, PAYOUT_WEI,
        coverage_ends, claim_deadline,
    ]
    policy_fingerprint = hashlib.sha256(
        b"BERMOND-POLICY-V2|" + json.dumps(policy_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    manifest.setdefault("live_cases", []).append(
        {
            "id": bond_id,
            "expected": "ACTIVE_RELEASE" if args.release_test else "BREACHED",
            "baseline_url": f"{FIXTURE_BASE}/baseline.txt",
            "current_url": f"{FIXTURE_BASE}/breached.txt",
            "provider": provider.address,
            "beneficiary": beneficiary.address,
            "payout_wei": PAYOUT_WEI,
            "policy_fingerprint": policy_fingerprint,
            "baseline_identity": baseline_identity,
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
        baseline_identity["document_id"],
        baseline_identity["publisher"],
        baseline_identity["version"],
        f"{FIXTURE_BASE}/breached.txt",
        json.dumps(terms, separators=(",", ":")),
        PAYOUT_WEI,
        coverage_ends,
        claim_deadline,
    ]
    receipts = []
    receipts.append(submit(client, provider, address, "create_bond", call_args))
    receipts.append(submit(client, provider, address, "enroll_subscriber", [bond_id, beneficiary.address]))
    receipts.append(submit(client, beneficiary, address, "accept_bond", [bond_id, policy_fingerprint]))
    receipts.append(submit(client, provider, address, "fund_bond", [bond_id], PAYOUT_WEI))
    if args.release_test:
        manifest = read_manifest()
        for case in manifest.get("live_cases", []):
            if case["id"] == bond_id:
                case["receipts"] = [item for item in manifest.get("lifecycle_transactions", []) if item.get("bond_id") == bond_id]
                case["state"] = "ACTIVE_RELEASE_WAIT"
                case["claim_deadline"] = claim_deadline
                case["release_eligible_after"] = claim_deadline + 1
        manifest["blocker"] = "Expiry release test bond is active and funded; run --release-case after its recorded deadline."
        write_manifest(manifest)
        print(f"bond_id={bond_id}")
        print(f"claim_deadline={claim_deadline}")
        return 0
    try:
        receipts.append(submit(client, beneficiary, address, "check_policy", [bond_id]))
    except RuntimeError:
        manifest = read_manifest()
        check_receipt = next(
            (
                item for item in reversed(manifest.get("lifecycle_transactions", []))
                if item.get("bond_id") == bond_id and item.get("function") == "check_policy"
            ),
            None,
        )
        try:
            bond = client.read_contract(
                address,
                "get_bond",
                args=[bond_id],
                account=beneficiary,
                transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
            )
        except GenLayerError:
            bond = None
        for case in manifest.get("live_cases", []):
            if case.get("id") == bond_id:
                case["receipts"] = [
                    item for item in manifest.get("lifecycle_transactions", [])
                    if item.get("bond_id") == bond_id
                ]
                outcome = str((check_receipt or {}).get("consensus_outcome", "")).casefold()
                case["state"] = (
                    "CHECK_CONSENSUS_UNDETERMINED"
                    if outcome == "undetermined"
                    else "CHECK_NOT_ACCEPTED"
                )
                case["last_verdict"] = None
                if bond is not None:
                    case["post_check_state"] = {
                        "state": bond.get("state"),
                        "checks": bond.get("checks"),
                        "last_verdict": bond.get("last_verdict"),
                        "pending_wei": bond.get("pending_wei"),
                        "reserved_wei": bond.get("reserved_wei"),
                    }
        manifest["blocker"] = (
            "Policy check did not reach accepted consensus; no result was persisted and no claim was submitted."
        )
        write_manifest(manifest)
        raise

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
    if bond is None:
        manifest = read_manifest()
        for case in manifest.get("live_cases", []):
            if case.get("id") == bond_id:
                case["receipts"] = [
                    item for item in manifest.get("lifecycle_transactions", [])
                    if item.get("bond_id") == bond_id
                ]
                case["state"] = "CHECK_FINALIZED_STATE_READ_UNAVAILABLE"
                case["claim_deadline"] = claim_deadline
                case["release_eligible_after"] = claim_deadline + 1
        manifest["blocker"] = "Policy check finalized, but the finalized state read failed; no claim was submitted."
        write_manifest(manifest)
        raise RuntimeError("Finalized state is unavailable after the check; claim withheld.")

    if int(bond.get("checks", 0)) < 1 or not bond.get("last_fingerprint"):
        manifest = read_manifest()
        for case in manifest.get("live_cases", []):
            if case.get("id") == bond_id:
                case["state"] = "CHECK_FINALIZED_STATE_INCONSISTENT"
                case["post_check_state"] = {
                    "state": bond.get("state"),
                    "checks": bond.get("checks"),
                    "last_verdict": bond.get("last_verdict"),
                    "last_fingerprint": bond.get("last_fingerprint"),
                }
        manifest["blocker"] = "Finalized check receipt did not produce a corresponding finalized state update; claim withheld."
        write_manifest(manifest)
        raise RuntimeError("The finalized check did not persist a verdict; claim withheld.")

    print(f"bond_state_after_check={bond.get('state')}")
    print(f"last_verdict={bond.get('last_verdict')}")
    balance_before_claim = None
    balance_after_claim = None
    post_claim_bond = None
    if bond.get("state") == "BREACHED":
        try:
            balance_before_claim = int(client.get_balance(beneficiary.address, block_identifier="finalized"))
        except GenLayerError as exc:
            print(f"beneficiary_balance_before_claim_unavailable={exc}", flush=True)
        try:
            receipts.append(submit(client, beneficiary, address, "claim_compensation", [bond_id]))
        except RuntimeError as exc:
            print(f"claim_result={exc}")
        try:
            post_claim_bond = client.read_contract(
                address,
                "get_bond",
                args=[bond_id],
                account=beneficiary,
                transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
            )
        except GenLayerError as exc:
            print(f"post_claim_state_read_unavailable={exc}", flush=True)
        try:
            balance_after_claim = int(client.get_balance(beneficiary.address, block_identifier="finalized"))
        except GenLayerError as exc:
            print(f"beneficiary_balance_after_claim_unavailable={exc}", flush=True)
    else:
        print("claim_result=not submitted because the finalized policy check did not authorize a breach")

    manifest = read_manifest()
    for case in manifest.get("live_cases", []):
        if case["id"] == bond_id:
            case["receipts"] = [
                item for item in manifest.get("lifecycle_transactions", [])
                if item.get("bond_id") == bond_id
            ]
            if bond.get("state") == "BREACHED":
                successful_claim = any(
                    item.get("function") == "claim_compensation" and item.get("successful")
                    for item in case["receipts"]
                )
                case["state"] = (
                    "CLAIM_FINALIZED_STATE_VERIFIED"
                    if post_claim_bond
                    and successful_claim
                    and beneficiary.address.lower() in post_claim_bond.get("claimed", [])
                    else "CLAIM_FINALIZED_STATE_READ_UNAVAILABLE"
                )
                if post_claim_bond:
                    case["post_claim_state"] = {
                        "state": post_claim_bond.get("state"),
                        "claimed": beneficiary.address.lower() in post_claim_bond.get("claimed", []),
                        "pending_wei": post_claim_bond.get("pending_wei"),
                        "paid_wei": post_claim_bond.get("paid_wei"),
                        "reserved_wei": post_claim_bond.get("reserved_wei"),
                    }
            else:
                case["state"] = bond.get("state", "UNKNOWN")
            case["last_verdict"] = bond.get("last_verdict")
            case["claim_deadline"] = claim_deadline
            case["release_eligible_after"] = claim_deadline + 1
            case["beneficiary_balance_before_claim_wei"] = balance_before_claim
            case["beneficiary_balance_after_claim_wei"] = balance_after_claim
            case["beneficiary_balance_delta_wei"] = (
                balance_after_claim - balance_before_claim
                if balance_before_claim is not None and balance_after_claim is not None
                else None
            )
    manifest["status"] = "DEPLOYED_VERIFIED"
    if bond.get("state") == "BREACHED":
        manifest["blocker"] = "Breach claim tested; inspect the finalized receipt, post-claim state and beneficiary balance delta. Contract accounting retains emitted EOA transfers as pending until settlement is independently reconciled."
    else:
        manifest["blocker"] = "Policy check finalized without an accepted breach; claim was correctly withheld. Expiry-release testing remains separate."
    write_manifest(manifest)
    print(f"bond_id={bond_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
