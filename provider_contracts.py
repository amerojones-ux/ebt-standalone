"""Fail-closed validation of captured provider evidence; no network or credentials."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Any

@dataclass(frozen=True)
class Contract:
    host: str
    endpoint: str
    fields: Mapping[str, type]
    max_age_seconds: int

@dataclass(frozen=True)
class Capture:
    host: str
    endpoint: str
    status: int
    body: Mapping[str, Any]
    published_at: str
    retrieved_at: str
    provenance_id: str


def parse_time(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def verify(contract: Contract, capture: Capture | None, *, now: datetime, reconciled_ids: frozenset[str]):
    if capture is None:
        return 'NOT_TESTED', 'NO_CAPTURE'
    if capture.host != contract.host or capture.endpoint != contract.endpoint:
        return 'FAIL', 'CONTRACT_MISMATCH'
    if capture.status in (401, 403):
        return 'FAIL', 'AUTHORIZATION_FAILED'
    if capture.status == 429:
        return 'HOLD', 'RATE_LIMITED'
    if capture.status != 200:
        return 'HOLD', 'HTTP_NOT_SUCCESS'
    if not isinstance(capture.body, Mapping):
        return 'FAIL', 'INVALID_BODY'
    for field, expected in contract.fields.items():
        value = capture.body.get(field)
        if value is None or type(value) is not expected or (expected is str and not value.strip()):
            return 'FAIL', 'FIELD_SCHEMA_INVALID'
    pub, ret = parse_time(capture.published_at), parse_time(capture.retrieved_at)
    if now.tzinfo is None or pub is None or ret is None or contract.max_age_seconds < 0:
        return 'HOLD', 'TIME_UNVERIFIED'
    current = now.astimezone(timezone.utc)
    if not pub <= ret <= current:
        return 'HOLD', 'TIME_ORDER_INVALID'
    if (current - pub).total_seconds() > contract.max_age_seconds:
        return 'HOLD', 'STALE_SOURCE'
    if not capture.provenance_id or capture.provenance_id not in reconciled_ids:
        return 'HOLD', 'PROVENANCE_NOT_RECONCILED'
    return 'PASS', 'CAPTURE_GATES_PASSED'
