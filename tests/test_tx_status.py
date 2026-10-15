from tools.tx_status import accepted_finalized_execution


def test_undetermined_finalized_transaction_is_not_success_even_when_leader_ran():
    result = {"lifecycle": {"state": "finalized", "outcome": "undetermined"}}

    assert not accepted_finalized_execution(result, leader_execution_succeeded=True)


def test_only_accepted_finalized_leader_execution_is_success():
    result = {"lifecycle": {"state": "finalized", "outcome": "accepted"}}

    assert accepted_finalized_execution(result, leader_execution_succeeded=True)
    assert not accepted_finalized_execution(result, leader_execution_succeeded=False)


def test_pending_or_missing_lifecycle_is_not_success():
    assert not accepted_finalized_execution(
        {"lifecycle": {"state": "pending", "outcome": "accepted"}},
        leader_execution_succeeded=True,
    )
    assert not accepted_finalized_execution({}, leader_execution_succeeded=True)
