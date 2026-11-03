"""Claim-bound readiness-evidence ledger validation.

No network or secret access. Readiness flags may be true only when a reviewed,
claim-specific evidence record exists and uses an allowed source type.
"""
from datetime import datetime, timezone
import re

from provider_live_request_plan import request_plan_sha256 as canonical_request_plan_sha256

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
PROVIDER_SOURCE_POLICY = {
    "live_auth_verified": {"github_actions_receipt"},
    "entitlement_verified": {"manual_review", "validation_report"},
    "identity_verified": {"validation_report"},
    "freshness_verified": {"validation_report"},
    "model_evidence_allowed": {"validation_report"},
}
MODEL_SOURCE_POLICY = {
    "source_provenance_verified": {"validation_report"},
    "roster_injury_identity_verified": {"validation_report"},
    "historical_calibration_verified": {"validation_report"},
    "joint_dependence_verified": {"validation_report"},
}
SHA40 = re.compile(r"^[0-9a-f]{40}$", re.I)
SHA64 = re.compile(r"^[0-9a-f]{64}$", re.I)
RUN_REF = re.compile(r"^github-actions-run:[0-9]+$")
REVIEW_REF = re.compile(r"^review:[A-Za-z0-9._:/-]+$")
REPORT_REF = re.compile(r"^validation-report:[A-Za-z0-9._:/-]+$")
REVIEWER = re.compile(r"^github:[A-Za-z0-9-]+#[0-9]+$")
ACTOR = re.compile(r"^[A-Za-z0-9-]+$")
ACTOR_ID = re.compile(r"^[0-9]+$")
RUN_ID = re.compile(r"^[0-9]+$")
SOURCE_REPOSITORY = "amerojones-ux/ebt-standalone"
REVIEW_WORKFLOW = ".github/workflows/provider-live-auth-evidence-review.yml"
SIGNER_WORKFLOWS = {
    "WeatherAPI": ".github/workflows/weatherapi-live-probe.yml",
    "The Odds API": ".github/workflows/theoddsapi-live-probe.yml",
    "API-Sports": ".github/workflows/apisports-status-probe.yml",
}

def _parse_time(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)

def _allowed_sources(subject, claim):
    if subject in PROVIDERS:
        return PROVIDER_SOURCE_POLICY.get(claim, set())
    if subject == "MODEL":
        return MODEL_SOURCE_POLICY.get(claim, set())
    return set()

def validate_record(record, *, subject, claim, trusted_now=None):
    errors = []
    if not isinstance(record, dict):
        return ["evidence record must be object"]

    required = {
        "status", "subject", "claim", "source_type",
        "reference", "reviewed_at", "reviewer",
    }
    provenance_fields = {
        "source_repository", "source_commit", "receipt_sha256",
        "artifact_sha256", "attestation_marker_sha256", "request_plan_sha256",
        "attestation_id",
        "attestation_url", "signer_workflow",
        "execution_intent_verified","execution_intent_sha256",
        "execution_intent_file_sha256","execution_intent_marker_sha256",
        "execution_intent_bundle_sha256","execution_intent_attestation_id",
        "execution_intent_attestation_url","execution_actor",
        "execution_actor_id","execution_max_requests",
        "review_repository", "review_workflow_run_id", "review_source_commit",
        "review_github_metadata_match", "review_decision_sha256",
        "review_decision_file_sha256", "review_attestation_marker_sha256",
        "review_attestation_id", "review_attestation_url",
        "review_signer_workflow",
    }
    allowed = required | provenance_fields
    if set(record) != (required | (set(record) & provenance_fields)):
        if set(record) - allowed:
            errors.append("unexpected evidence fields")
        if required - set(record):
            errors.append("missing evidence fields")

    if record.get("status") != "VERIFIED":
        errors.append("status must be VERIFIED")
    if record.get("subject") != subject:
        errors.append("subject mismatch")
    if record.get("claim") != claim:
        errors.append("claim mismatch")

    source_type = record.get("source_type")
    if source_type not in SOURCE_TYPES:
        errors.append("invalid source_type")
    elif source_type not in _allowed_sources(subject, claim):
        errors.append("source_type not allowed for claim")

    reference = record.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        errors.append("reference required")
    elif source_type == "github_actions_receipt" and not RUN_REF.fullmatch(reference):
        errors.append("invalid github actions reference")
    elif source_type == "manual_review" and not REVIEW_REF.fullmatch(reference):
        errors.append("invalid manual review reference")
    elif source_type == "validation_report" and not REPORT_REF.fullmatch(reference):
        errors.append("invalid validation report reference")

    reviewed_at = _parse_time(record.get("reviewed_at"))
    if reviewed_at is None:
        errors.append("timezone-aware reviewed_at required")
    elif trusted_now is not None:
        now = _parse_time(trusted_now)
        if now is None:
            errors.append("trusted_now must be timezone-aware")
        elif reviewed_at > now:
            errors.append("reviewed_at cannot be in the future")

    reviewer = record.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        errors.append("reviewer required")

    source_repository = record.get("source_repository")
    source_commit = record.get("source_commit")
    receipt_sha = record.get("receipt_sha256")
    artifact_sha = record.get("artifact_sha256")
    marker_sha = record.get("attestation_marker_sha256")
    request_plan_sha = record.get("request_plan_sha256")
    attestation_id = record.get("attestation_id")
    attestation_url = record.get("attestation_url")
    signer_workflow = record.get("signer_workflow")
    execution_intent_verified = record.get("execution_intent_verified")
    execution_intent_sha = record.get("execution_intent_sha256")
    execution_intent_file_sha = record.get("execution_intent_file_sha256")
    execution_intent_marker_sha = record.get("execution_intent_marker_sha256")
    execution_intent_bundle_sha = record.get("execution_intent_bundle_sha256")
    execution_intent_attestation_id = record.get("execution_intent_attestation_id")
    execution_intent_attestation_url = record.get("execution_intent_attestation_url")
    execution_actor = record.get("execution_actor")
    execution_actor_id = record.get("execution_actor_id")
    execution_max_requests = record.get("execution_max_requests")
    review_repository = record.get("review_repository")
    review_workflow_run_id = record.get("review_workflow_run_id")
    review_source_commit = record.get("review_source_commit")
    review_github_metadata_match = record.get("review_github_metadata_match")
    review_decision_sha = record.get("review_decision_sha256")
    review_decision_file_sha = record.get("review_decision_file_sha256")
    review_marker_sha = record.get("review_attestation_marker_sha256")
    review_attestation_id = record.get("review_attestation_id")
    review_attestation_url = record.get("review_attestation_url")
    review_signer_workflow = record.get("review_signer_workflow")
    if source_commit is not None and (
        not isinstance(source_commit, str) or not SHA40.fullmatch(source_commit)
    ):
        errors.append("invalid source_commit")
    if receipt_sha is not None and (
        not isinstance(receipt_sha, str) or not SHA64.fullmatch(receipt_sha)
    ):
        errors.append("invalid receipt_sha256")
    if artifact_sha is not None and (
        not isinstance(artifact_sha, str) or not SHA64.fullmatch(artifact_sha)
    ):
        errors.append("invalid artifact_sha256")
    if marker_sha is not None and (
        not isinstance(marker_sha, str) or not SHA64.fullmatch(marker_sha)
    ):
        errors.append("invalid attestation_marker_sha256")
    if request_plan_sha is not None and (
        not isinstance(request_plan_sha, str) or not SHA64.fullmatch(request_plan_sha)
    ):
        errors.append("invalid request_plan_sha256")
    for label,value in (
        ("execution_intent_sha256",execution_intent_sha),
        ("execution_intent_file_sha256",execution_intent_file_sha),
        ("execution_intent_marker_sha256",execution_intent_marker_sha),
        ("execution_intent_bundle_sha256",execution_intent_bundle_sha),
    ):
        if value is not None and (
            not isinstance(value,str) or not SHA64.fullmatch(value)
        ):
            errors.append("invalid "+label)
    if review_source_commit is not None and (
        not isinstance(review_source_commit, str)
        or not SHA40.fullmatch(review_source_commit)
    ):
        errors.append("invalid review_source_commit")
    for label, value in (
        ("review_decision_sha256", review_decision_sha),
        ("review_decision_file_sha256", review_decision_file_sha),
        ("review_attestation_marker_sha256", review_marker_sha),
    ):
        if value is not None and (
            not isinstance(value, str) or not SHA64.fullmatch(value)
        ):
            errors.append("invalid " + label)

    if source_type == "github_actions_receipt":
        if source_repository != SOURCE_REPOSITORY:
            errors.append("github_actions_receipt source_repository mismatch")
        if source_commit is None:
            errors.append("github_actions_receipt requires source_commit")
        if receipt_sha is None:
            errors.append("github_actions_receipt requires receipt_sha256")
        if artifact_sha is None:
            errors.append("github_actions_receipt requires artifact_sha256")
        if marker_sha is None:
            errors.append("github_actions_receipt requires attestation_marker_sha256")
        if request_plan_sha is None:
            errors.append("github_actions_receipt requires request_plan_sha256")
        elif request_plan_sha != canonical_request_plan_sha256(subject):
            errors.append("github_actions_receipt request_plan_sha256 mismatch")
        if execution_intent_verified is not True:
            errors.append("github_actions_receipt requires execution_intent_verified")
        for label,value in (
            ("execution_intent_sha256",execution_intent_sha),
            ("execution_intent_file_sha256",execution_intent_file_sha),
            ("execution_intent_marker_sha256",execution_intent_marker_sha),
            ("execution_intent_bundle_sha256",execution_intent_bundle_sha),
        ):
            if value is None:
                errors.append("github_actions_receipt requires "+label)
        if (
            not isinstance(execution_intent_attestation_id,str)
            or not execution_intent_attestation_id
        ):
            errors.append(
                "github_actions_receipt requires execution_intent_attestation_id"
            )
        if (
            not isinstance(execution_intent_attestation_url,str)
            or not execution_intent_attestation_url.startswith(
                "https://github.com/" + SOURCE_REPOSITORY + "/attestations/"
            )
        ):
            errors.append(
                "github_actions_receipt execution_intent_attestation_url mismatch"
            )
        if (
            not isinstance(execution_actor,str)
            or not ACTOR.fullmatch(execution_actor)
            or not isinstance(execution_actor_id,str)
            or not ACTOR_ID.fullmatch(execution_actor_id)
        ):
            errors.append("github_actions_receipt execution actor identity invalid")
        if type(execution_max_requests) is not int or execution_max_requests!=1:
            errors.append(
                "github_actions_receipt execution_max_requests must equal 1"
            )
        if not isinstance(attestation_id, str) or not attestation_id:
            errors.append("github_actions_receipt requires attestation_id")
        if not isinstance(attestation_url, str) or not attestation_url.startswith(
            "https://github.com/" + SOURCE_REPOSITORY + "/attestations/"
        ):
            errors.append("github_actions_receipt attestation_url mismatch")
        expected_signer = SIGNER_WORKFLOWS.get(subject)
        if expected_signer is None:
            errors.append("github_actions_receipt signer workflow not configured")
        elif signer_workflow != expected_signer:
            errors.append("github_actions_receipt signer_workflow mismatch")

        if not isinstance(reviewer, str) or not REVIEWER.fullmatch(reviewer):
            errors.append("github_actions_receipt reviewer must be GitHub actor identity")
        if review_repository != SOURCE_REPOSITORY:
            errors.append("github_actions_receipt review_repository mismatch")
        if not isinstance(review_workflow_run_id, str) or not RUN_ID.fullmatch(
            review_workflow_run_id
        ):
            errors.append("github_actions_receipt review_workflow_run_id invalid")
        if review_source_commit is None:
            errors.append("github_actions_receipt requires review_source_commit")
        if review_github_metadata_match is not True:
            errors.append("github_actions_receipt requires review_github_metadata_match")
        if review_decision_sha is None:
            errors.append("github_actions_receipt requires review_decision_sha256")
        if review_decision_file_sha is None:
            errors.append("github_actions_receipt requires review_decision_file_sha256")
        if review_marker_sha is None:
            errors.append("github_actions_receipt requires review_attestation_marker_sha256")
        if not isinstance(review_attestation_id, str) or not review_attestation_id:
            errors.append("github_actions_receipt requires review_attestation_id")
        if not isinstance(review_attestation_url, str) or not review_attestation_url.startswith(
            "https://github.com/" + SOURCE_REPOSITORY + "/attestations/"
        ):
            errors.append("github_actions_receipt review_attestation_url mismatch")
        if review_signer_workflow != REVIEW_WORKFLOW:
            errors.append("github_actions_receipt review_signer_workflow mismatch")
    else:
        attestation_only = {
            "source_repository": source_repository,
            "receipt_sha256": receipt_sha,
            "attestation_marker_sha256": marker_sha,
            "request_plan_sha256": request_plan_sha,
            "attestation_id": attestation_id,
            "attestation_url": attestation_url,
            "signer_workflow": signer_workflow,
            "execution_intent_verified": execution_intent_verified,
            "execution_intent_sha256": execution_intent_sha,
            "execution_intent_file_sha256": execution_intent_file_sha,
            "execution_intent_marker_sha256": execution_intent_marker_sha,
            "execution_intent_bundle_sha256": execution_intent_bundle_sha,
            "execution_intent_attestation_id": execution_intent_attestation_id,
            "execution_intent_attestation_url": execution_intent_attestation_url,
            "execution_actor": execution_actor,
            "execution_actor_id": execution_actor_id,
            "execution_max_requests": execution_max_requests,
            "review_repository": review_repository,
            "review_workflow_run_id": review_workflow_run_id,
            "review_source_commit": review_source_commit,
            "review_github_metadata_match": review_github_metadata_match,
            "review_decision_sha256": review_decision_sha,
            "review_decision_file_sha256": review_decision_file_sha,
            "review_attestation_marker_sha256": review_marker_sha,
            "review_attestation_id": review_attestation_id,
            "review_attestation_url": review_attestation_url,
            "review_signer_workflow": review_signer_workflow,
        }
        if any(value is not None for value in attestation_only.values()):
            errors.append("attestation provenance fields require github_actions_receipt")
    if source_type == "validation_report" and artifact_sha is None:
        errors.append("validation_report requires artifact_sha256")

    return errors

def validate_ledger(ledger, *, trusted_now=None):
    errors = []
    if not isinstance(ledger, dict):
        return ["ledger must be object"]
    if ledger.get("schema_version") != 5:
        errors.append("schema_version must be 5")

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
                errors.extend(
                    name + " " + claim + ": " + e
                    for e in validate_record(
                        record, subject=name, claim=claim, trusted_now=trusted_now
                    )
                )

    if seen != PROVIDERS:
        errors.append("evidence provider coverage incomplete")

    model = ledger.get("model_gates")
    if not isinstance(model, dict) or set(model) != MODEL_CLAIMS:
        errors.append("model evidence claim coverage mismatch")
    else:
        for claim, record in model.items():
            if record is not None:
                errors.extend(
                    claim + ": " + e
                    for e in validate_record(
                        record, subject="MODEL", claim=claim, trusted_now=trusted_now
                    )
                )
    return errors

def evidence_supports_readiness(readiness, ledger, *, trusted_now=None):
    errors = validate_ledger(ledger, trusted_now=trusted_now)
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
                elif validate_record(
                    record, subject=name, claim=claim, trusted_now=trusted_now
                ):
                    errors.append(name + " " + claim + " evidence invalid")

    model = readiness.get("model_gates", {})
    model_evidence = ledger.get("model_gates", {}) if isinstance(ledger, dict) else {}
    if isinstance(model, dict):
        for claim in MODEL_CLAIMS:
            if model.get(claim) is True:
                record = model_evidence.get(claim)
                if record is None:
                    errors.append(claim + " lacks evidence")
                elif validate_record(
                    record, subject="MODEL", claim=claim, trusted_now=trusted_now
                ):
                    errors.append(claim + " evidence invalid")
    return errors
