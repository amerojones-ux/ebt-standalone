"""Immutable daily Black Diamond audit ledger.

Builds on ebt_validation's SHA-256 hash-chain primitive while enforcing V7
record separation and legal lifecycle transitions. Pregame evidence, final
settlement, postgame reverse-engine findings, and model-learning reviews remain
separate append-only records.

This module does not fetch data, forecast, settle a wager, or change model
weights.
"""
import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, Mapping
from zoneinfo import ZoneInfo

from ebt_validation import record_hash, validate_chain

CENTRAL = ZoneInfo("America/Chicago")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PRE_GAME_TYPES = {
    "PREGAME_SOURCE_EVIDENCE",
    "PREGAME_MODEL_ARTIFACT",
    "PREGAME_FORECAST_LOCK",
    "PREGAME_DECISION",
    "ROLE_REVALIDATION",
    "MARKET_SNAPSHOT",
    "MC_RECEIPT",
    "SHADOW_CANDIDATE",
    "REJECTED_CANDIDATE",
}
FINAL_TYPES = {"SETTLEMENT"}
POSTGAME_TYPES = {"POSTGAME_REVERSE_AUDIT"}
REVIEW_TYPES = {"CALIBRATION_REVIEW", "LEARNING_REVIEW"}
RECORD_TYPES = PRE_GAME_TYPES | FINAL_TYPES | POSTGAME_TYPES | REVIEW_TYPES

V7_VERDICTS = {"APPROVED", "HOLD", "PASS", "REJECT", "NO_QUALIFYING_PROP"}
SOURCE_STATUSES = {
    "FOUND", "N/A", "BLOCKED", "STALE", "CONFLICTING", "ADAPTER UNAVAILABLE"
}
IDENTIFIABILITY = {
    "PRE_GAME_IDENTIFIABLE",
    "PARTIALLY_IDENTIFIABLE",
    "POSTGAME_ONLY",
}
VARIANCE_CLASS = {
    "STRUCTURAL_CANDIDATE",
    "MIXED_OR_UNCERTAIN",
    "RANDOM_OR_UNRESOLVED",
}
MC_PURPOSES = {
    "MC1_BASELINE",
    "MC2_ADVERSARIAL",
    "MC3_SCENARIO_CORRELATION",
    "FINAL_JOINT_PARLAY",
}


def _clock(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return dt.astimezone(timezone.utc)


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{field} lowercase SHA-256 required")
    return value


def _nonblank(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} required")
    return value.strip()


def _artifact_refs(value):
    if not isinstance(value, list):
        raise ValueError("artifact_refs array required")
    out = []
    seen = set()
    for item in value:
        if (
            not isinstance(item, Mapping)
            or set(item) != {"kind", "sha256"}
        ):
            raise ValueError("exact artifact_ref schema required")
        kind = _nonblank(item["kind"], "artifact_ref.kind")
        digest = _sha(item["sha256"], "artifact_ref.sha256")
        key = (kind, digest)
        if key in seen:
            raise ValueError("duplicate artifact_ref")
        seen.add(key)
        out.append({"kind": kind, "sha256": digest})
    return out


def _event_date_ct(event_start: datetime) -> str:
    return event_start.astimezone(CENTRAL).date().isoformat()


def _review_date_ct(recorded_at: datetime) -> str:
    return recorded_at.astimezone(CENTRAL).date().isoformat()


def _validate_type_data(record_type: str, data: Mapping[str, Any]):
    if not isinstance(data, Mapping):
        raise ValueError("record data object required")

    if record_type == "PREGAME_SOURCE_EVIDENCE":
        if set(data) != {"source_role", "source_status", "evidence_sha256"}:
            raise ValueError("exact source-evidence data schema required")
        _nonblank(data["source_role"], "source_role")
        if data["source_status"] not in SOURCE_STATUSES:
            raise ValueError("invalid V7 source_status")
        _sha(data["evidence_sha256"], "evidence_sha256")

    elif record_type == "PREGAME_MODEL_ARTIFACT":
        if set(data) != {"artifact_type", "artifact_sha256", "status"}:
            raise ValueError("exact model-artifact data schema required")
        _nonblank(data["artifact_type"], "artifact_type")
        _sha(data["artifact_sha256"], "artifact_sha256")
        _nonblank(data["status"], "status")

    elif record_type == "PREGAME_FORECAST_LOCK":
        required = {
            "forecast_id", "model_version", "projection_sha256",
            "role_evidence_sha256", "forecast_status",
        }
        if set(data) != required:
            raise ValueError("exact forecast-lock data schema required")
        _nonblank(data["forecast_id"], "forecast_id")
        _nonblank(data["model_version"], "model_version")
        _sha(data["projection_sha256"], "projection_sha256")
        _sha(data["role_evidence_sha256"], "role_evidence_sha256")
        if data["forecast_status"] not in V7_VERDICTS:
            raise ValueError("invalid forecast_status")

    elif record_type == "PREGAME_DECISION":
        required = {
            "decision_id", "decision_version", "market_key",
            "verdict", "decision_sha256",
        }
        if set(data) != required:
            raise ValueError("exact pregame-decision data schema required")
        _nonblank(data["decision_id"], "decision_id")
        if type(data["decision_version"]) is not int or data["decision_version"] < 1:
            raise ValueError("positive decision_version required")
        _nonblank(data["market_key"], "market_key")
        if data["verdict"] not in V7_VERDICTS:
            raise ValueError("invalid decision verdict")
        _sha(data["decision_sha256"], "decision_sha256")

    elif record_type == "ROLE_REVALIDATION":
        required = {
            "prior_decision_id", "replacement_decision_version",
            "plan_sha256", "status",
        }
        if set(data) != required:
            raise ValueError("exact role-revalidation data schema required")
        _nonblank(data["prior_decision_id"], "prior_decision_id")
        if (
            type(data["replacement_decision_version"]) is not int
            or data["replacement_decision_version"] < 2
        ):
            raise ValueError("replacement_decision_version >=2 required")
        _sha(data["plan_sha256"], "plan_sha256")
        _nonblank(data["status"], "status")

    elif record_type == "MARKET_SNAPSHOT":
        required = {
            "snapshot_sha256", "model_locked_at",
            "complete_posted_ladder_verified", "price_identity_verified",
            "source_status",
        }
        if set(data) != required:
            raise ValueError("exact market-snapshot data schema required")
        _sha(data["snapshot_sha256"], "snapshot_sha256")
        _clock(data["model_locked_at"], "model_locked_at")
        if type(data["complete_posted_ladder_verified"]) is not bool:
            raise ValueError("complete_posted_ladder_verified boolean required")
        if type(data["price_identity_verified"]) is not bool:
            raise ValueError("price_identity_verified boolean required")
        if data["source_status"] not in SOURCE_STATUSES:
            raise ValueError("invalid market source_status")

    elif record_type == "MC_RECEIPT":
        required = {"purpose", "trials", "input_sha256", "code_sha256"}
        if set(data) != required:
            raise ValueError("exact MC receipt data schema required")
        if data["purpose"] not in MC_PURPOSES:
            raise ValueError("invalid MC purpose")
        if type(data["trials"]) is not int or data["trials"] < 100000:
            raise ValueError("MC receipt requires >=100000 trials")
        _sha(data["input_sha256"], "input_sha256")
        _sha(data["code_sha256"], "code_sha256")

    elif record_type == "SHADOW_CANDIDATE":
        if set(data) != {"candidate_id", "lane", "reason"}:
            raise ValueError("exact shadow-candidate data schema required")
        _nonblank(data["candidate_id"], "candidate_id")
        _nonblank(data["lane"], "lane")
        _nonblank(data["reason"], "reason")

    elif record_type == "REJECTED_CANDIDATE":
        if set(data) != {"candidate_id", "reason", "kill_switch"}:
            raise ValueError("exact rejected-candidate data schema required")
        _nonblank(data["candidate_id"], "candidate_id")
        _nonblank(data["reason"], "reason")
        _nonblank(data["kill_switch"], "kill_switch")

    elif record_type == "SETTLEMENT":
        required = {
            "decision_id", "settlement_version", "settlement", "actual",
            "official_result_verified", "result_source_sha256",
            "revision_reason",
        }
        if set(data) != required:
            raise ValueError("exact settlement data schema required")
        _nonblank(data["decision_id"], "decision_id")
        if (
            type(data["settlement_version"]) is not int
            or data["settlement_version"] < 1
        ):
            raise ValueError("positive settlement_version required")
        if data["settlement"] not in {"HIT", "MISS", "PUSH", "VOID"}:
            raise ValueError("invalid settlement")
        if data["official_result_verified"] is not True:
            raise ValueError("settlement requires verified official result")
        _sha(data["result_source_sha256"], "result_source_sha256")
        if data["revision_reason"] is not None:
            _nonblank(data["revision_reason"], "revision_reason")

    elif record_type == "POSTGAME_REVERSE_AUDIT":
        required = {
            "decision_id", "settlement_record_id", "identifiability",
            "variance_class", "mechanism", "failure_mechanism",
            "pregame_evidence_eligible",
        }
        if set(data) != required:
            raise ValueError("exact postgame reverse-audit data schema required")
        _nonblank(data["decision_id"], "decision_id")
        _nonblank(data["settlement_record_id"], "settlement_record_id")
        if data["identifiability"] not in IDENTIFIABILITY:
            raise ValueError("invalid postgame identifiability")
        if data["variance_class"] not in VARIANCE_CLASS:
            raise ValueError("invalid structural/random classification")
        _nonblank(data["mechanism"], "mechanism")
        _nonblank(data["failure_mechanism"], "failure_mechanism")
        if data["pregame_evidence_eligible"] is not False:
            raise ValueError("postgame audit can never be pregame evidence")

    elif record_type == "CALIBRATION_REVIEW":
        required = {
            "review_sha256", "status", "calibration_verified",
            "model_promotion_applied",
        }
        if set(data) != required:
            raise ValueError("exact calibration-review data schema required")
        _sha(data["review_sha256"], "review_sha256")
        _nonblank(data["status"], "status")
        if data["calibration_verified"] is not False:
            raise ValueError("audit review record cannot self-certify calibration")
        if data["model_promotion_applied"] is not False:
            raise ValueError("audit review record cannot promote model")

    elif record_type == "LEARNING_REVIEW":
        required = {
            "review_sha256", "status", "weight_change_applied",
            "threshold_change_applied", "model_promotion_applied",
        }
        if set(data) != required:
            raise ValueError("exact learning-review data schema required")
        _sha(data["review_sha256"], "review_sha256")
        _nonblank(data["status"], "status")
        if data["weight_change_applied"] is not False:
            raise ValueError("audit learning review cannot apply weights")
        if data["threshold_change_applied"] is not False:
            raise ValueError("audit learning review cannot apply thresholds")
        if data["model_promotion_applied"] is not False:
            raise ValueError("audit learning review cannot promote model")

    else:
        raise ValueError("unsupported audit record type")


def validate_audit_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    required = {
        "schema_version", "audit_date_ct", "record_type", "subject_id",
        "event_id", "event_start", "effective_at", "recorded_at",
        "supersedes_record_id", "artifact_refs", "data",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("exact immutable-audit payload schema required")
    if payload["schema_version"] != "1.0":
        raise ValueError("unsupported audit schema_version")
    if (
        not isinstance(payload["audit_date_ct"], str)
        or DATE_RE.fullmatch(payload["audit_date_ct"]) is None
    ):
        raise ValueError("audit_date_ct YYYY-MM-DD required")
    record_type = payload["record_type"]
    if record_type not in RECORD_TYPES:
        raise ValueError("unsupported audit record_type")
    _nonblank(payload["subject_id"], "subject_id")
    effective = _clock(payload["effective_at"], "effective_at")
    recorded = _clock(payload["recorded_at"], "recorded_at")
    if effective > recorded:
        raise ValueError("effective_at cannot follow recorded_at")
    supersedes = payload["supersedes_record_id"]
    if supersedes is not None:
        _nonblank(supersedes, "supersedes_record_id")
        if record_type not in {
            "PREGAME_DECISION", "SETTLEMENT", "POSTGAME_REVERSE_AUDIT"
        }:
            raise ValueError("record type may not supersede another record")

    event_id = payload["event_id"]
    event_start_raw = payload["event_start"]
    if record_type in REVIEW_TYPES:
        if event_id is not None or event_start_raw is not None:
            raise ValueError("global review record cannot claim event identity")
        expected_date = _review_date_ct(recorded)
    else:
        event_id = _nonblank(event_id, "event_id")
        event_start = _clock(event_start_raw, "event_start")
        expected_date = _event_date_ct(event_start)
        if record_type in PRE_GAME_TYPES:
            if not effective < event_start or not recorded < event_start:
                raise ValueError("pregame record must be effective and recorded before start")
        elif record_type in FINAL_TYPES | POSTGAME_TYPES:
            if effective < event_start or recorded < event_start:
                raise ValueError("final/postgame record cannot precede event start")
    if payload["audit_date_ct"] != expected_date:
        raise ValueError("audit_date_ct does not match event/review Central date")

    artifact_refs = _artifact_refs(payload["artifact_refs"])
    _validate_type_data(record_type, payload["data"])
    return {
        **payload,
        "artifact_refs": artifact_refs,
    }


def _decision_index(records):
    decisions = {}
    for record in records:
        payload = record["payload"]
        if payload["record_type"] == "PREGAME_DECISION":
            data = payload["data"]
            decisions.setdefault(data["decision_id"], []).append(record)
    return decisions


def validate_daily_audit_chain(records):
    """Validate hash chain plus V7 lifecycle/reference integrity."""
    if not isinstance(records, list):
        raise ValueError("audit record array required")
    last = validate_chain(records)
    by_id = {}
    decisions = {}
    settlements = {}

    for record in records:
        payload = validate_audit_payload(record["payload"])
        record_id = record["id"]
        by_id[record_id] = record
        record_type = payload["record_type"]
        data = payload["data"]
        supersedes = payload["supersedes_record_id"]

        if supersedes is not None:
            target = by_id.get(supersedes)
            if target is None or target["id"] == record_id:
                raise ValueError("superseded record must already exist")
            target_payload = target["payload"]
            if target_payload["record_type"] != record_type:
                raise ValueError("superseding revision must keep record_type")
            if target_payload["event_id"] != payload["event_id"]:
                raise ValueError("superseding revision must keep event_id")

        if record_type == "PREGAME_DECISION":
            decision_id = data["decision_id"]
            prior = decisions.get(decision_id)
            if prior is None:
                if data["decision_version"] != 1 or supersedes is not None:
                    raise ValueError("first decision version must be 1 without supersedes")
            else:
                if supersedes != prior["id"]:
                    raise ValueError("decision revision must supersede latest prior decision")
                prior_data = prior["payload"]["data"]
                if data["decision_version"] != prior_data["decision_version"] + 1:
                    raise ValueError("decision revision version must increment by one")
                if payload["event_id"] != prior["payload"]["event_id"]:
                    raise ValueError("decision revision event mismatch")
            decisions[decision_id] = record

        elif record_type == "ROLE_REVALIDATION":
            decision_id = data["prior_decision_id"]
            prior = decisions.get(decision_id)
            if prior is None:
                raise ValueError("role revalidation requires prior decision")
            prior_version = prior["payload"]["data"]["decision_version"]
            if data["replacement_decision_version"] != prior_version + 1:
                raise ValueError("role revalidation replacement version mismatch")
            if prior["payload"]["event_id"] != payload["event_id"]:
                raise ValueError("role revalidation event mismatch")

        elif record_type == "MARKET_SNAPSHOT":
            model_lock = _clock(data["model_locked_at"], "model_locked_at")
            effective = _clock(payload["effective_at"], "effective_at")
            if effective < model_lock:
                raise ValueError("market snapshot cannot predate model lock")

        elif record_type == "SETTLEMENT":
            decision_id = data["decision_id"]
            prior_decision = decisions.get(decision_id)
            if prior_decision is None:
                raise ValueError("settlement requires prior pregame decision")
            if prior_decision["payload"]["event_id"] != payload["event_id"]:
                raise ValueError("settlement event mismatch")
            prior_settlement = settlements.get(decision_id)
            if prior_settlement is None:
                if data["settlement_version"] != 1 or supersedes is not None:
                    raise ValueError("first settlement version must be 1")
            else:
                if supersedes != prior_settlement["id"]:
                    raise ValueError("settlement revision must supersede latest settlement")
                prior_data = prior_settlement["payload"]["data"]
                if data["settlement_version"] != prior_data["settlement_version"] + 1:
                    raise ValueError("settlement revision version must increment by one")
                if data["revision_reason"] is None:
                    raise ValueError("settlement revision requires revision_reason")
            settlements[decision_id] = record

        elif record_type == "POSTGAME_REVERSE_AUDIT":
            decision_id = data["decision_id"]
            if decision_id not in decisions:
                raise ValueError("postgame audit requires prior decision")
            settlement_record = by_id.get(data["settlement_record_id"])
            if (
                settlement_record is None
                or settlement_record["payload"]["record_type"] != "SETTLEMENT"
            ):
                raise ValueError("postgame audit requires referenced settlement record")
            if settlement_record["payload"]["data"]["decision_id"] != decision_id:
                raise ValueError("postgame audit decision/settlement mismatch")
            if settlement_record["payload"]["event_id"] != payload["event_id"]:
                raise ValueError("postgame audit event mismatch")
            if _clock(payload["effective_at"], "effective_at") < _clock(
                settlement_record["payload"]["effective_at"],
                "settlement.effective_at",
            ):
                raise ValueError("postgame audit cannot predate settlement")
            if supersedes is not None:
                prior_audit = by_id[supersedes]
                if prior_audit["payload"]["data"]["decision_id"] != decision_id:
                    raise ValueError("postgame audit revision decision mismatch")

    return last


def append_daily_audit_record(
    path,
    record_id,
    payload,
    *,
    expected_last_sha256,
):
    """Atomically validate references and append one immutable audit record."""
    _nonblank(record_id, "record_id")
    _sha(expected_last_sha256, "expected_last_sha256")
    validate_audit_payload(payload)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        text = handle.read()
        if text and not text.endswith("\n"):
            raise ValueError("incomplete audit ledger tail")
        records = [json.loads(line) for line in text.splitlines()]
        last = validate_daily_audit_chain(records)
        if last != expected_last_sha256:
            raise ValueError("stale or truncated audit ledger")
        if any(record["id"] == record_id for record in records):
            raise ValueError("duplicate audit record id")
        record = {
            "id": record_id,
            "previous_sha256": last,
            "payload": dict(payload),
        }
        record["sha256"] = record_hash(record)
        validate_daily_audit_chain(records + [record])
        encoded = json.dumps(
            record, sort_keys=True, separators=(",", ":"), allow_nan=False
        ) + "\n"
        handle.seek(0, os.SEEK_END)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
        return record["sha256"]


def summarize_daily_audit(records):
    """Return audit coverage/status without changing any record."""
    last = validate_daily_audit_chain(records)
    counts = {record_type: 0 for record_type in sorted(RECORD_TYPES)}
    event_ids = set()
    decision_ids = set()
    settlement_ids = set()
    for record in records:
        payload = record["payload"]
        counts[payload["record_type"]] += 1
        if payload["event_id"] is not None:
            event_ids.add(payload["event_id"])
        if payload["record_type"] == "PREGAME_DECISION":
            decision_ids.add(payload["data"]["decision_id"])
        if payload["record_type"] == "SETTLEMENT":
            settlement_ids.add(payload["data"]["decision_id"])
    unsettled = sorted(decision_ids - settlement_ids)
    return {
        "mode": "IMMUTABLE_DAILY_AUDIT_SUMMARY",
        "record_count": len(records),
        "event_count": len(event_ids),
        "record_type_counts": counts,
        "decision_count": len(decision_ids),
        "settled_decision_count": len(settlement_ids),
        "unsettled_decision_ids": unsettled,
        "last_sha256": last,
        "pregame_records_immutable": True,
        "postgame_backfill_into_pregame_forbidden": True,
        "model_weights_changed_by_audit": False,
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
    }
