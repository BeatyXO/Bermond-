"""Small, SDK-independent checks for finalized GenLayer transaction outcomes."""
from __future__ import annotations


def accepted_finalized_execution(result: dict, leader_execution_succeeded: bool) -> bool:
    """Return true only when the leader ran and the protocol accepted consensus."""
    lifecycle = result.get("lifecycle") or {}
    return (
        str(lifecycle.get("state", "")).casefold() == "finalized"
        and str(lifecycle.get("outcome", "")).casefold() == "accepted"
        and leader_execution_succeeded
    )
