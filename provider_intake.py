"""Provider intake inventory. This module makes no external calls and reads no secrets.

Provider metadata is a planned integration inventory, not verified subscription evidence.
"""
from dataclasses import dataclass
from enum import Enum

class IntakeStatus(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    HOLD = "HOLD"
    FAIL = "FAIL"
    VERIFIED = "VERIFIED"

@dataclass(frozen=True)
class ProviderIntake:
    provider: str
    api_host: str | None
    endpoint_id: str | None
    contract_version: str | None
    credential_present: bool | None
    authorized_read_only: bool | None
    schema_pass: bool | None
    source_authenticated: bool | None
    official_reconciled: bool | None
    evidence_id: str | None

PROVIDERS = ("TheRundown", "Sportsdata", "The Odds API", "API-Sports",
             "RapidAPI", "WeatherAPI", "Sportradar")

def evaluate_intake(record: ProviderIntake) -> tuple[IntakeStatus, tuple[str, ...]]:
    if record.provider not in PROVIDERS:
        return IntakeStatus.FAIL, ("UNKNOWN_PROVIDER",)
    if not record.api_host or not record.endpoint_id or not record.contract_version:
        return IntakeStatus.NOT_TESTED, ("ENDPOINT_CONTRACT_UNDEFINED",)
    gates = {
        "CREDENTIAL_NOT_CONFIRMED": record.credential_present,
        "READ_ONLY_AUTH_UNVERIFIED": record.authorized_read_only,
        "SCHEMA_UNVERIFIED": record.schema_pass,
        "SOURCE_AUTH_UNVERIFIED": record.source_authenticated,
        "OFFICIAL_RECONCILIATION_UNVERIFIED": record.official_reconciled,
    }
    failed = tuple(k for k,v in gates.items() if v is False)
    if failed:
        return IntakeStatus.FAIL, failed
    pending = tuple(k for k,v in gates.items() if v is not True)
    if not record.evidence_id:
        pending += ("EVIDENCE_ID_MISSING",)
    if pending:
        return IntakeStatus.HOLD, pending
    return IntakeStatus.VERIFIED, ()

def untested_inventory() -> tuple[ProviderIntake, ...]:
    return tuple(ProviderIntake(p,None,None,None,None,None,None,None,None,None) for p in PROVIDERS)
