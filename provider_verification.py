"""Offline, fail-closed provider evidence verification. No network or secrets."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

class Verdict(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    FAIL = "FAIL"
    NOT_TESTED = "NOT_TESTED"

@dataclass(frozen=True)
class EndpointContract:
    provider: str
    endpoint_id: str
    required_fields: tuple[str, ...]
    max_age_seconds: int
    requires_official_reconciliation: bool = True

@dataclass(frozen=True)
class Evidence:
    http_status: int | None
    payload: Mapping[str, Any] | None
    published_at: str | None
    retrieved_at: str | None
    official_reconciled: bool | None
    authorized: bool | None

@dataclass(frozen=True)
class GateResult:
    verdict: Verdict
    reasons: tuple[str, ...]

def _utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None

def evaluate(contract: EndpointContract, evidence: Evidence | None, *, now: datetime) -> GateResult:
    """Return evidence status only; PASS is not forecast or production approval."""
    if evidence is None or evidence.http_status is None:
        return GateResult(Verdict.NOT_TESTED, ("NO_REQUEST_EVIDENCE",))
    if evidence.http_status in (401, 403) or evidence.authorized is False:
        return GateResult(Verdict.FAIL, ("AUTHORIZATION_FAILED",))
    if evidence.http_status == 429:
        return GateResult(Verdict.HOLD, ("RATE_LIMITED",))
    if evidence.http_status != 200:
        return GateResult(Verdict.FAIL if 400 <= evidence.http_status < 500 else Verdict.HOLD, ("HTTP_UNEXPECTED",))
    if evidence.authorized is not True:
        return GateResult(Verdict.HOLD, ("AUTHORIZATION_UNCONFIRMED",))
    if not isinstance(evidence.payload, Mapping):
        return GateResult(Verdict.FAIL, ("INVALID_PAYLOAD",))
    missing = tuple(f for f in contract.required_fields if f not in evidence.payload or evidence.payload[f] is None)
    if missing:
        return GateResult(Verdict.FAIL, ("REQUIRED_FIELDS_MISSING",))
    published, retrieved = _utc(evidence.published_at), _utc(evidence.retrieved_at)
    clock = now.astimezone(timezone.utc) if now.tzinfo else None
    if not published or not retrieved or not clock or contract.max_age_seconds < 0:
        return GateResult(Verdict.HOLD, ("TIMESTAMP_UNVERIFIED",))
    if published > retrieved or retrieved > clock or published > clock:
        return GateResult(Verdict.HOLD, ("TIMESTAMP_ORDER_INVALID",))
    if (clock - published).total_seconds() > contract.max_age_seconds:
        return GateResult(Verdict.HOLD, ("SOURCE_STALE",))
    if contract.requires_official_reconciliation and evidence.official_reconciled is not True:
        return GateResult(Verdict.HOLD, ("OFFICIAL_RECONCILIATION_PENDING",))
    return GateResult(Verdict.PASS, ("ENDPOINT_EVIDENCE_GATES_PASSED",))
