"""Evidence-ledger validation for provider/model readiness claims.

No network or secret access. A readiness flag may be true only when a reviewed
evidence record exists for that exact claim.
"""
from datetime import datetime
import re

PROVIDERS = {
    "TheRundown",
    "SportsDataIO",
    "The Odds API",
    "API-Sports",
    "RapidAPI",
    "WeatherAPI",
    "Sportradar",
}
PROVIDER_CLAIMS = {
    "live_auth_verified",
    "entitlement_verified",
    "identity_verified",
    "freshness_verified",
    "model_evidence_allowed",
}
MODEL_CLAIMS = {
    "source_provenance_verified",
    "roster_injury_identity_verified",
    "historical_calibration_verified",
    "joint_dependence_verified",
}
SOURCE_TYPES = {"github_actions_receipt", "manual_review", "validation_report"}
SHA40 = re.compile(r"^[0-9a-f]{40}$", re.I)
SHA64 = re.compile(r"^[0-9a-f]{64}$", re.I)

def _valid_time(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None

def validate_record(record):
    errors = []
    if not isinstance(record, dict):
        return ["evidence record must be object"]
    required = {"status", "source_type", "reference", "reviewed_at", "reviewer"}
    allowed = required | {"source_commit", "artifact_sha256"}
    if set(record) - allowed:
        errors.append("unexpected evidence fields")
    if record.get("status") != "VERIFIED":
        errors.append("status must be VERIFIED")
    if record.get("source_type") not in SOURCE_TYPES:
        errors.append("invalid source_type")
    if not isinstance(record.get("reference"), str) or not record["reference"].strip():
        errors.append("reference required")
    if not _valid_time(record.get("reviewed_at")):
        errors.append("timezone-aware reviewed_at required")
    if not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
        errors.append("reviewer required")

    source_commit = record.get("source_commit")
    artifact_sha = record.get("artifact_sha256")
    if source_commit is not None and (not isinstance(source_commit, str) or not SHA40.fullmatch(source_commit)):
        errors.append("invalid source_commit")
    if artifact_sha is not None and (not isinstance(artifact_sha, str) or not SHA64.fullmatch(artifact_sha)):
        errors.append("invalid artifact_sha256")

    if record.get("source_type") == "github_actions_receipt":
        if source_commit is None:
            errors.append("github_actions_receipt requires source_commit")
        if artifact_sha is None:
            errors.append("github_actions_receipt requires artifact_sha256")
    return errors

def validate_ledger(ledger):
    errors = []
    if not isinstance(ledger, dict):
        return ["ledger must be object"]
    if ledger.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    entries = ledger.get("providers")
    if not isinstance(entries, list):
        return errors + ["providers must be list"]

    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("provider evidence entry must be object")
            continue
        name = entry.get("name")
        if name not in PROVIDERS:
            errors.append("unknown evidence provider")
            continue
        if name in seen:
            errors.append("duplicate evidence provider: " + name)
        seen.add(name)
        evidence = entry.get("evidence")
        if not isinstance(evidence, dict) or set(evidence) != PROVIDER_CLAIMS:
            errors.append(name + " evidence claim coverage mismatch")
            continue
        for claim, record in evidence.items():
            if record is not None:
                errors.extend(name + " " + claim + ": " + e for e in validate_record(record))

    if seen != PROVIDERS:
        errors.append("evidence provider coverage incomplete")

    model = ledger.get("model_gates")
    if not isinstance(model, dict) or set(model) != MODEL_CLAIMS:
        errors.append("model evidence claim coverage mismatch")
    else:
        for claim, record in model.items():
            if record is not None:
                errors.extend(claim + ": " + e for e in validate_record(record))
    return errors

def evidence_supports_readiness(readiness, ledger):
    errors = validate_ledger(ledger)
    if not isinstance(readiness, dict):
        return errors + ["readiness must be object"]

    entries = ledger.get("providers", []) if isinstance(ledger, dict) else []
    evidence_by_name = {
        entry.get("name"): entry.get("evidence", {})
        for entry in entries
        if isinstance(entry, dict)
    }
    providers = readiness.get("providers", [])
    if not isinstance(providers, list):
        return errors + ["readiness providers must be list"]

    for entry in providers:
        if not isinstance(entry, dict):
            errors.append("readiness provider entry must be object")
            continue
        name = entry.get("name")
        evidence = evidence_by_name.get(name, {})
        for claim in PROVIDER_CLAIMS:
            if entry.get(claim) is True:
                record = evidence.get(claim)
                if record is None:
                    errors.append(name + " " + claim + " lacks evidence")
                elif validate_record(record):
                    errors.append(name + " " + claim + " evidence invalid")

    model = readiness.get("model_gates", {})
    model_evidence = ledger.get("model_gates", {}) if isinstance(ledger, dict) else {}
    if isinstance(model, dict):
        for claim in MODEL_CLAIMS:
            if model.get(claim) is True:
                record = model_evidence.get(claim)
                if record is None:
                    errors.append(claim + " lacks evidence")
                elif validate_record(record):
                    errors.append(claim + " evidence invalid")
    return errors
