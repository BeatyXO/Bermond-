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
BASELINE_URL = "https://archive.example.org/bermond/baseline.txt"
LIVE_URL = "https://provider.example.org/policy"
TERMS = {
    "allowance": "At least 100,000 requests per month.",
    "retention": "Delete customer data within 30 days.",
    "refunds": "Refund customers after a qualifying service failure.",
    "notice": "Give customers 30 days notice before material changes.",
}


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
        LIVE_URL,
        json.dumps(TERMS),
        1_000,
        int((now + timedelta(days=2)).timestamp()),
        int((now + timedelta(days=3)).timestamp()),
    )
    contract.enroll_subscriber("direct-001", direct_alice)
    direct_vm.value = 1_000
    contract.fund_bond("direct-001")

    bond = contract.get_bond("direct-001")
    assert bond["state"] == "ACTIVE"
    assert bond["reserved_wei"] == 1_000
    assert bond["subscribers"] == [str(direct_alice).lower()]
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
        LIVE_URL,
        json.dumps(TERMS),
        1_000,
        int((now + timedelta(days=2)).timestamp()),
        int((now + timedelta(days=3)).timestamp()),
    )
    contract.enroll_subscriber("direct-002", direct_alice)
    direct_vm.value = 999
    with direct_vm.expect_revert("exact bond value required"):
        contract.fund_bond("direct-002")
    assert contract.get_bond("direct-002")["state"] == "DRAFT"
