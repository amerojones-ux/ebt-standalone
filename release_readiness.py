"""Fail-closed release decision for EBT.ai sports data and forecasting.

No API calls, secrets, deployments, or sportsbook transactions.
A readiness claim must be backed by independently validated evidence.
"""
from dataclasses import dataclass
from enum import Enum

class State(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    FAIL = "FAIL"
    NOT_TESTED = "NOT_TESTED"

@dataclass(frozen=True)
class ReleaseEvidence:
    provider_endpoints: State
    source_authentication: State
    official_reconciliation: State
    identity_and_availability: State
    independent_model_lock: State
    out_of_sample_calibration: State
    three_monte_carlo_runs: State
    market_separation: State
    rollback_rehearsal: State
    operator_approval: State

REQUIRED = tuple(ReleaseEvidence.__dataclass_fields__)

@dataclass(frozen=True)
class ReleaseDecision:
    status: str
    blockers: tuple[str, ...]

def decide(evidence: ReleaseEvidence) -> ReleaseDecision:
    blockers = tuple(name for name in REQUIRED if getattr(evidence, name) is not State.PASS)
    if blockers:
        return ReleaseDecision("HOLD", blockers)
    return ReleaseDecision("READY_FOR_CONTROLLED_RELEASE_REVIEW", ())

def all_unverified() -> ReleaseEvidence:
    return ReleaseEvidence(*(State.NOT_TESTED for _ in REQUIRED))
