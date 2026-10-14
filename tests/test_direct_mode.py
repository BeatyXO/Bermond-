"""Native GenLayer Direct Mode smoke tests.

These run against the GenLayer test VM and the SDK pinned by the contract's
Depends header. They complement tests/test_contract.py, which uses a fake VM.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest


BASELINE = "A committed service policy with four protected promises."
CURRENT_POLICY = "Current policy text with a changed quota."
BASELINE_URL = "https://archive.example.org/bermond/baseline.txt"
LIVE_URL = "https://provider.example.org/policy"
TERMS = {
    "allowance": "At least 100,000 requests per month.",
    "retention": "Delete customer data within 30 days.",
    "refunds": "Refund customers after a qualifying service failure.",
    "notice": "Give customers 30 days notice before material changes.",
}
PROMPT_PATTERN = "Bermond's independent policy-drift examiner"


def _classification(allowance: str) -> dict[str, object]:
    statuses = {
        "allowance": allowance,
        "retention": "UNCHANGED",
        "refunds": "UNCHANGED",
        "notice": "UNCHANGED",
    }
    return {
        "criteria": [
            {
                "dimension": dimension,
                "status": statuses[dimension],
                "witness": "both",
                "evidence": [
                    {"source": "baseline", "quote": "A committed service policy", "sha256": hashlib.sha256(BASELINE.encode()).hexdigest()},
                    {"source": "current", "quote": "Current policy text", "sha256": hashlib.sha256(CURRENT_POLICY.encode()).hexdigest()},
                ],
                "fact": "Compared against the committed baseline and current policy.",
            }
            for dimension in ("allowance", "retention", "refunds", "notice")
        ],
        "reasoning": "Classified only the four protected service promises.",
    }


def _funded_contract(direct_vm, direct_deploy, direct_alice, additional=()):
    now = datetime.now(timezone.utc)
    direct_vm.warp(now.isoformat())
    contract = direct_deploy("contracts/bermond.py")
    contract.create_bond(
        "direct-web-001",
        "Direct Mode Service",
        "API",
        BASELINE_URL,
        hashlib.sha256(BASELINE.encode()).hexdigest(),
        "direct-policy-v1",
        "Direct Mode Service",
        "2026-10-13",
        LIVE_URL,
        json.dumps(TERMS),
        1_000,
        int((now + timedelta(days=2)).timestamp()),
        int((now + timedelta(days=3)).timestamp()),
    )
    beneficiaries = [direct_alice, *additional]
    for beneficiary in beneficiaries:
        contract.enroll_subscriber("direct-web-001", beneficiary)
    provider = direct_vm.sender
    fingerprint = contract.get_bond("direct-web-001")["policy_fingerprint"]
    for beneficiary in beneficiaries:
        direct_vm.sender = beneficiary
        contract.accept_bond("direct-web-001", fingerprint)
    direct_vm.sender = provider
    direct_vm.value = 1_000 * len(beneficiaries)
    contract.fund_bond("direct-web-001")
    direct_vm.value = 0
    direct_vm.mock_web("archive.example.org", {"status": 200, "body": BASELINE})
    direct_vm.mock_web("provider.example.org", {"status": 200, "body": CURRENT_POLICY})
    return contract


@pytest.mark.direct
def test_native_vm_persists_bond_and_freezes_enrollment(direct_vm, direct_deploy, direct_alice, direct_bob):
    now = datetime.now(timezone.utc)
    direct_vm.warp(now.isoformat())
    contract = direct_deploy("contracts/bermond.py")
    contract.create_bond(
        "direct-001",
        "Direct Mode Service",
        "API",
        BASELINE_URL,
        hashlib.sha256(BASELINE.encode()).hexdigest(),
        "direct-policy-v1",
        "Direct Mode Service",
        "2026-10-13",
        LIVE_URL,
        json.dumps(TERMS),
        1_000,
        int((now + timedelta(days=2)).timestamp()),
        int((now + timedelta(days=3)).timestamp()),
    )
    contract.enroll_subscriber("direct-001", direct_alice)
    provider = direct_vm.sender
    direct_vm.sender = direct_alice
    contract.accept_bond("direct-001", contract.get_bond("direct-001")["policy_fingerprint"])
    direct_vm.sender = provider
    direct_vm.value = 1_000
    contract.fund_bond("direct-001")

    bond = contract.get_bond("direct-001")
    assert bond["state"] == "ACTIVE"
    assert bond["reserved_wei"] == 1_000
    assert bond["subscribers"] == [f"0x{direct_alice.hex()}".lower()]
    with direct_vm.expect_revert("enrollment frozen"):
        contract.enroll_subscriber("direct-001", direct_bob)


@pytest.mark.direct
def test_native_vm_rejects_non_exact_payable_funding(direct_vm, direct_deploy, direct_alice):
    now = datetime.now(timezone.utc)
    direct_vm.warp(now.isoformat())
    contract = direct_deploy("contracts/bermond.py")
    contract.create_bond(
        "direct-002",
        "Direct Mode Service",
        "API",
        BASELINE_URL,
        hashlib.sha256(BASELINE.encode()).hexdigest(),
        "direct-policy-v1",
        "Direct Mode Service",
        "2026-10-13",
        LIVE_URL,
        json.dumps(TERMS),
        1_000,
        int((now + timedelta(days=2)).timestamp()),
        int((now + timedelta(days=3)).timestamp()),
    )
    contract.enroll_subscriber("direct-002", direct_alice)
    provider = direct_vm.sender
    direct_vm.sender = direct_alice
    contract.accept_bond("direct-002", contract.get_bond("direct-002")["policy_fingerprint"])
    direct_vm.sender = provider
    direct_vm.value = 999
    with direct_vm.expect_revert("exact bond value required"):
        contract.fund_bond("direct-002")
    assert contract.get_bond("direct-002")["state"] == "DRAFT"


@pytest.mark.direct
def test_native_duplicate_bond_and_unaccepted_beneficiary_are_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    now = datetime.now(timezone.utc)
    direct_vm.warp(now.isoformat())
    contract = direct_deploy("contracts/bermond.py")
    args = (
        "direct-consent-001", "Direct Mode Service", "API", BASELINE_URL,
        hashlib.sha256(BASELINE.encode()).hexdigest(), "direct-policy-v1",
        "Direct Mode Service", "2026-10-13", LIVE_URL, json.dumps(TERMS), 1_000,
        int((now + timedelta(days=2)).timestamp()), int((now + timedelta(days=3)).timestamp()),
    )
    fingerprint = contract.create_bond(*args)
    with direct_vm.expect_revert("bond ID exists"):
        contract.create_bond(*args)
    contract.enroll_subscriber(args[0], direct_alice)
    direct_vm.value = 1_000
    with direct_vm.expect_revert("all beneficiaries must accept"):
        contract.fund_bond(args[0])
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("policy fingerprint mismatch"):
        contract.accept_bond(args[0], "0" * 64)
    contract.accept_bond(args[0], fingerprint)
    with direct_vm.expect_revert("already accepted"):
        contract.accept_bond(args[0], fingerprint)
    provider_hex = contract.get_bond(args[0])["provider"]
    direct_vm.sender = bytes.fromhex(provider_hex[2:])
    with direct_vm.expect_revert("enrollment frozen"):
        contract.enroll_subscriber(args[0], direct_bob)
    contract.fund_bond(args[0])
    assert contract.get_bond(args[0])["accepted"] == [f"0x{direct_alice.hex()}".lower()]


@pytest.mark.direct
def test_native_breach_claim_replay_and_partial_expiry_release(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = _funded_contract(direct_vm, direct_deploy, direct_alice, [direct_bob])
    deadline = contract.get_bond("direct-web-001")["claim_deadline"]
    direct_vm.mock_llm(PROMPT_PATTERN, json.dumps(_classification("BREACHED")))
    result = contract.check_policy("direct-web-001")
    assert result["verdict"] == "BREACHED"

    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("not enrolled"):
        contract.claim_compensation("direct-web-001")
    direct_vm.sender = direct_alice
    contract.claim_compensation("direct-web-001")
    with direct_vm.expect_revert("claim already paid"):
        contract.claim_compensation("direct-web-001")
    record = contract.get_bond("direct-web-001")
    assert record["reserved_wei"] == 1_000
    assert record["pending_wei"] == 1_000
    assert record["funded_wei"] == record["paid_wei"] + record["released_wei"] + record["reserved_wei"] + record["pending_wei"]

    provider_hex = contract.get_bond("direct-web-001")["provider"]
    direct_vm.sender = bytes.fromhex(provider_hex[2:])
    with direct_vm.expect_revert("claim window is still open"):
        contract.release_collateral("direct-web-001")
    after_deadline = datetime.fromtimestamp(deadline + 1, tz=timezone.utc)
    direct_vm.warp(after_deadline.isoformat())
    contract.release_collateral("direct-web-001")
    record = contract.get_bond("direct-web-001")
    assert record["state"] == "CLOSED"
    assert record["paid_wei"] == 0 and record["released_wei"] == 0
    assert record["pending_wei"] == 2_000
    assert record["funded_wei"] == record["paid_wei"] + record["released_wei"] + record["reserved_wei"] + record["pending_wei"]
    with direct_vm.expect_revert("already released"):
        contract.release_collateral("direct-web-001")


@pytest.mark.direct
def test_native_unavailable_and_malformed_evidence_are_nonpaying_unresolved(direct_vm, direct_deploy, direct_alice):
    contract = _funded_contract(direct_vm, direct_deploy, direct_alice)
    direct_vm.clear_mocks()
    direct_vm.mock_web("archive.example.org", {"status": 200, "body": BASELINE})
    assert contract.check_policy("direct-web-001")["verdict"] == "UNRESOLVED"
    assert contract.get_bond("direct-web-001")["reserved_wei"] == 1_000

    direct_vm.clear_mocks()
    direct_vm.mock_web("archive.example.org", {"status": 200, "body": BASELINE})
    direct_vm.mock_web("provider.example.org", {"status": 200, "body": CURRENT_POLICY})
    direct_vm.mock_llm(PROMPT_PATTERN, json.dumps({"malformed": True}))
    assert contract.check_policy("direct-web-001")["verdict"] == "UNRESOLVED"
    assert contract.get_bond("direct-web-001")["reserved_wei"] == 1_000


@pytest.mark.direct
def test_native_web_render_and_validator_disagreement_fail_closed(direct_vm, direct_deploy, direct_alice):
    contract = _funded_contract(direct_vm, direct_deploy, direct_alice)
    compliant = _classification("UNCHANGED")
    direct_vm.mock_llm(PROMPT_PATTERN, json.dumps(compliant))

    result = contract.check_policy("direct-web-001")
    assert result["verdict"] == "COMPLIANT", (result, direct_vm._traces)

    # Direct Mode captures the validator callback. Give the simulated validator
    # a separately obtained answer and require disagreement to reject the leader.
    direct_vm.clear_mocks()
    direct_vm.mock_web("archive.example.org", {"status": 200, "body": BASELINE})
    direct_vm.mock_web("provider.example.org", {"status": 200, "body": CURRENT_POLICY})
    direct_vm.mock_llm(PROMPT_PATTERN, json.dumps(_classification("BREACHED")))
    assert direct_vm.run_validator(leader_result=compliant) is False
    assert contract.get_bond("direct-web-001")["state"] == "ACTIVE"
