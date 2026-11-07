"""Immutable role/market revalidation state machine for Black Diamond.

A materially changed official role state revokes the prior event decision. The
replacement path must rebuild the independent projection first, run all three
>=100k simulations, then ingest a fresh complete market ladder after the new
projection lock. This module never approves a wager.
"""
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Dict, Mapping

SHA64=re.compile(r"^[0-9a-f]{64}$")
DECISION_STATUSES={"APPROVED","HOLD","PASS","REJECT","NO_QUALIFYING_PROP"}


def _clock(value: Any, field: str) -> datetime:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return dt.astimezone(timezone.utc)


def _sha(value: Any, field: str) -> str:
    if not isinstance(value,str) or SHA64.fullmatch(value) is None:
        raise ValueError(f"{field} lowercase SHA-256 required")
    return value


def _canonical_sha(payload: Mapping[str,Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    ).hexdigest()


def _prior(record: Mapping[str,Any]) -> Dict[str,Any]:
    required={
        "decision_id","decision_version","event_id","event_key","model_version",
        "projection_locked_at","role_evidence_sha256","market_snapshot_sha256",
        "market_captured_at","decision_status",
    }
    if not isinstance(record,Mapping) or set(record)!=required:
        raise ValueError("exact prior decision schema required")
    for field in ("decision_id","event_id","event_key","model_version"):
        if not isinstance(record[field],str) or not record[field].strip():
            raise ValueError(f"{field} nonblank string required")
    if type(record["decision_version"]) is not int or record["decision_version"]<1:
        raise ValueError("positive integer decision_version required")
    if record["decision_status"] not in DECISION_STATUSES:
        raise ValueError("invalid prior decision_status")
    lock=_clock(record["projection_locked_at"],"projection_locked_at")
    market=_clock(record["market_captured_at"],"market_captured_at")
    if market < lock:
        raise ValueError("prior market snapshot predates projection lock")
    _sha(record["role_evidence_sha256"],"role_evidence_sha256")
    _sha(record["market_snapshot_sha256"],"market_snapshot_sha256")
    return dict(record)


def _current_role_state(record: Mapping[str,Any]) -> Dict[str,Any]:
    required={
        "event_id","event_key","role_evidence_sha256","role_evidence_available_at",
        "game_gate_status","full_rerun_required","hold_for_confirmation",
        "change_count","affected_player_ids",
    }
    if not isinstance(record,Mapping) or set(record)!=required:
        raise ValueError("exact current role state schema required")
    if record["game_gate_status"] not in {"FOUND","HOLD"}:
        raise ValueError("game_gate_status must be FOUND or HOLD")
    if type(record["full_rerun_required"]) is not bool or type(record["hold_for_confirmation"]) is not bool:
        raise ValueError("role rerun/hold flags must be boolean")
    if type(record["change_count"]) is not int or record["change_count"]<0:
        raise ValueError("nonnegative change_count required")
    players=record["affected_player_ids"]
    if not isinstance(players,list) or any(not isinstance(x,str) or not x.strip() for x in players):
        raise ValueError("affected_player_ids must be string array")
    if len(players)!=len(set(players)):
        raise ValueError("duplicate affected player id")
    _sha(record["role_evidence_sha256"],"role_evidence_sha256")
    _clock(record["role_evidence_available_at"],"role_evidence_available_at")
    return dict(record)


def plan_event_revalidation(
    prior_decision: Mapping[str,Any],
    current_role_state: Mapping[str,Any],
) -> Dict[str,Any]:
    """Decide whether immutable prior decision must be revoked."""
    prior=_prior(prior_decision)
    current=_current_role_state(current_role_state)
    if current["event_id"]!=prior["event_id"] or current["event_key"]!=prior["event_key"]:
        raise ValueError("role state does not match prior event")
    prior_lock=_clock(prior["projection_locked_at"],"projection_locked_at")
    role_time=_clock(current["role_evidence_available_at"],"role_evidence_available_at")
    evidence_changed=current["role_evidence_sha256"]!=prior["role_evidence_sha256"]
    material=current["full_rerun_required"] or current["change_count"]>0
    gate_hold=current["game_gate_status"]=="HOLD" or current["hold_for_confirmation"]

    reasons=[]
    if gate_hold:
        reasons.append("CURRENT_ROLE_GATE_HOLD")
    if material:
        reasons.append("MATERIAL_ROLE_STATE_CHANGE")
    if material and not evidence_changed:
        reasons.append("ROLE_CHANGE_WITHOUT_EVIDENCE_VERSION_CHANGE")
    if material and role_time<=prior_lock:
        reasons.append("ROLE_CHANGE_NOT_NEWER_THAN_PRIOR_LOCK")
    if evidence_changed and not material:
        reasons.append("NONMATERIAL_ROLE_EVIDENCE_REFRESH")

    provenance_conflict=(
        (material and not evidence_changed)
        or (material and role_time<=prior_lock)
    )
    revoke=gate_hold or material or provenance_conflict
    if provenance_conflict:
        status="HOLD_PROVENANCE_CONFLICT"
    elif gate_hold:
        status="HOLD_ROLE_CONFIRMATION"
    elif material:
        status="REVALIDATION_REQUIRED"
    else:
        status="PRIOR_DECISION_REMAINS_ELIGIBLE"

    next_version=prior["decision_version"]+1 if revoke else prior["decision_version"]
    plan_body={
        "prior_decision_id":prior["decision_id"],
        "event_id":prior["event_id"],
        "event_key":prior["event_key"],
        "prior_decision_version":prior["decision_version"],
        "replacement_decision_version":next_version,
        "current_role_evidence_sha256":current["role_evidence_sha256"],
        "current_role_evidence_available_at":current["role_evidence_available_at"],
        "prior_decision_revoked":revoke,
        "provenance_conflict":provenance_conflict,
        "status":status,
        "reasons":reasons,
    }
    plan_sha=_canonical_sha(plan_body)
    required_steps=[] if not revoke else [
        "CONFIRM_ROLE_GATE_FOUND",
        "REBUILD_INDEPENDENT_PROJECTION",
        "RUN_MC1_BASELINE_100K_PLUS",
        "RUN_MC2_ADVERSARIAL_100K_PLUS",
        "RUN_MC3_SCENARIO_CORRELATION_100K_PLUS",
        "INGEST_FRESH_COMPLETE_MARKET_LADDER_AFTER_MODEL_LOCK",
        "RECALCULATE_PRICE_EV_UNCERTAINTY_SCENARIO_SURVIVAL",
        "RUN_FINAL_V7_REVALIDATION",
    ]
    return {
        "mode":"IMMUTABLE_ROLE_MARKET_REVALIDATION_PLAN",
        **plan_body,
        "plan_sha256":plan_sha,
        "affected_player_ids":list(current["affected_player_ids"]),
        "required_steps":required_steps,
        "prior_market_snapshot_revoked":revoke,
        "forecast_status":"HOLD" if revoke else prior["decision_status"],
        "wager_status":"NOT APPROVED" if revoke else "UNCHANGED_BY_THIS_MODULE",
    }


def role_state_from_nba_injury(
    canonical_report: Mapping[str,Any],
    injury_diff: Mapping[str,Any],
    game_gate: Mapping[str,Any],
    *,
    event_key: str,
) -> Dict[str,Any]:
    """Bridge canonical NBA official injury evidence into the immutable trigger."""
    if not isinstance(canonical_report,Mapping) or not isinstance(canonical_report.get("rows"),list):
        raise ValueError("canonical NBA injury report required")
    if not isinstance(injury_diff,Mapping) or not isinstance(injury_diff.get("changes"),list):
        raise ValueError("NBA injury diff required")
    if not isinstance(game_gate,Mapping) or game_gate.get("event_key")!=event_key:
        raise ValueError("matching NBA injury game gate required")
    event_rows=[row for row in canonical_report["rows"] if row.get("event_key")==event_key]
    if not event_rows:
        raise ValueError("event absent from canonical NBA injury report")
    event_ids={row.get("event_id") for row in event_rows}
    if len(event_ids)!=1 or None in event_ids:
        raise ValueError("single canonical event_id required")
    report_times={row.get("report_time_utc") for row in event_rows}
    if len(report_times)!=1:
        raise ValueError("single report timestamp required")
    role_hash=_canonical_sha({
        "event_key":event_key,
        "rows":[{
            key:row.get(key) for key in (
                "event_id","team_id","player_id","row_type","current_status",
                "reason","submission_status","report_time_utc","captured_at",
            )
        } for row in sorted(
            event_rows,
            key=lambda x:(str(x.get("team_id")),str(x.get("player_id")),x.get("row_type",""))
        )],
    })
    event_changes=[]
    affected=[]
    for change in injury_diff["changes"]:
        if not isinstance(change,Mapping):
            raise ValueError("injury diff changes must be objects")
        key=change.get("key")
        if not isinstance(key,list) or not key or key[0]!=event_key:
            continue
        event_changes.append(change)
        if len(key)>=3 and isinstance(key[2],str) and key[2].strip():
            affected.append(key[2])
    affected=sorted(set(affected))
    return {
        "event_id":next(iter(event_ids)),
        "event_key":event_key,
        "role_evidence_sha256":role_hash,
        "role_evidence_available_at":next(iter(report_times)),
        "game_gate_status":game_gate.get("status"),
        "full_rerun_required":bool(event_changes) or injury_diff.get("full_rerun_required") is True,
        "hold_for_confirmation":(
            game_gate.get("status")!="FOUND"
            or injury_diff.get("hold_for_confirmation") is True
        ),
        "change_count":len(event_changes),
        "affected_player_ids":affected,
    }


def _verify_plan_hash(plan: Mapping[str,Any]) -> None:
    body={
        "prior_decision_id":plan.get("prior_decision_id"),
        "event_id":plan.get("event_id"),
        "event_key":plan.get("event_key"),
        "prior_decision_version":plan.get("prior_decision_version"),
        "replacement_decision_version":plan.get("replacement_decision_version"),
        "current_role_evidence_sha256":plan.get("current_role_evidence_sha256"),
        "current_role_evidence_available_at":plan.get("current_role_evidence_available_at"),
        "prior_decision_revoked":plan.get("prior_decision_revoked"),
        "provenance_conflict":plan.get("provenance_conflict"),
        "status":plan.get("status"),
        "reasons":plan.get("reasons"),
    }
    if _canonical_sha(body)!=plan.get("plan_sha256"):
        raise ValueError("revalidation plan hash mismatch")


def assess_revalidation_completion(
    plan: Mapping[str,Any],
    *,
    current_role_gate: Mapping[str,Any],
    rerun_receipt: Mapping[str,Any],
    market_receipt: Mapping[str,Any],
) -> Dict[str,Any]:
    """Verify ordering/provenance before handing replacement to final V7 qualify()."""
    if not isinstance(plan,Mapping) or plan.get("mode")!="IMMUTABLE_ROLE_MARKET_REVALIDATION_PLAN":
        raise ValueError("revalidation plan required")
    if plan.get("prior_decision_revoked") is not True:
        raise ValueError("completion only applies to revoked decisions")
    _sha(plan.get("plan_sha256"),"plan_sha256")
    _verify_plan_hash(plan)
    if plan.get("provenance_conflict") is True:
        return {
            "mode":"ROLE_MARKET_REVALIDATION_COMPLETION",
            "status":"HOLD",
            "reasons":["UNRESOLVED_PROVENANCE_CONFLICT"],
            "ready_for_final_v7_qualification":False,
            "wager_status":"NOT APPROVED",
        }

    gate_required={"event_id","event_key","status","role_evidence_sha256","available_at"}
    if not isinstance(current_role_gate,Mapping) or set(current_role_gate)!=gate_required:
        raise ValueError("exact current_role_gate schema required")
    if current_role_gate["event_id"]!=plan["event_id"] or current_role_gate["event_key"]!=plan["event_key"]:
        raise ValueError("role gate event mismatch")
    _sha(current_role_gate["role_evidence_sha256"],"current_role_gate.role_evidence_sha256")
    role_time=_clock(current_role_gate["available_at"],"current_role_gate.available_at")

    rerun_required={
        "event_id","decision_version","model_version","role_evidence_sha256",
        "projection_sha256","projection_locked_at","mc_runs",
    }
    if not isinstance(rerun_receipt,Mapping) or set(rerun_receipt)!=rerun_required:
        raise ValueError("exact rerun_receipt schema required")
    if rerun_receipt["event_id"]!=plan["event_id"]:
        raise ValueError("rerun event mismatch")
    if rerun_receipt["decision_version"]!=plan["replacement_decision_version"]:
        raise ValueError("replacement decision version mismatch")
    if not isinstance(rerun_receipt["model_version"],str) or not rerun_receipt["model_version"].strip():
        raise ValueError("model_version required")
    _sha(rerun_receipt["role_evidence_sha256"],"rerun.role_evidence_sha256")
    _sha(rerun_receipt["projection_sha256"],"projection_sha256")
    projection_lock=_clock(rerun_receipt["projection_locked_at"],"projection_locked_at")
    runs=rerun_receipt["mc_runs"]
    if not isinstance(runs,Mapping) or set(runs)!={"baseline","adversarial","scenario"}:
        raise ValueError("baseline/adversarial/scenario MC receipts required")
    mc_errors=[]
    for purpose,run in runs.items():
        if not isinstance(run,Mapping) or set(run)!={"trials","input_sha256","code_sha256"}:
            mc_errors.append(f"{purpose}:invalid_schema")
            continue
        if type(run["trials"]) is not int or run["trials"]<100000:
            mc_errors.append(f"{purpose}:trials")
        try:
            _sha(run["input_sha256"],f"{purpose}.input_sha256")
            _sha(run["code_sha256"],f"{purpose}.code_sha256")
        except ValueError:
            mc_errors.append(f"{purpose}:provenance")

    market_required={
        "event_id","market_snapshot_sha256","captured_at","oldest_quote_at",
        "complete_posted_ladder_verified","price_identity_verified",
    }
    if not isinstance(market_receipt,Mapping) or set(market_receipt)!=market_required:
        raise ValueError("exact market_receipt schema required")
    if market_receipt["event_id"]!=plan["event_id"]:
        raise ValueError("market event mismatch")
    _sha(market_receipt["market_snapshot_sha256"],"market_snapshot_sha256")
    market_capture=_clock(market_receipt["captured_at"],"market.captured_at")
    oldest_quote=_clock(market_receipt["oldest_quote_at"],"market.oldest_quote_at")
    if type(market_receipt["complete_posted_ladder_verified"]) is not bool:
        raise ValueError("complete_posted_ladder_verified boolean required")
    if type(market_receipt["price_identity_verified"]) is not bool:
        raise ValueError("price_identity_verified boolean required")

    reasons=[]
    if current_role_gate["status"]!="FOUND":
        reasons.append("ROLE_GATE_NOT_FOUND")
    if current_role_gate["role_evidence_sha256"]!=plan["current_role_evidence_sha256"]:
        reasons.append("ROLE_EVIDENCE_CHANGED_AGAIN")
    if rerun_receipt["role_evidence_sha256"]!=current_role_gate["role_evidence_sha256"]:
        reasons.append("PROJECTION_NOT_BOUND_TO_CURRENT_ROLE_EVIDENCE")
    if projection_lock < role_time:
        reasons.append("PROJECTION_LOCK_PRECEDES_CURRENT_ROLE_EVIDENCE")
    reasons.extend("MC_"+x for x in mc_errors)
    if market_capture < projection_lock:
        reasons.append("MARKET_CAPTURE_PRECEDES_NEW_PROJECTION_LOCK")
    if oldest_quote < projection_lock:
        reasons.append("MARKET_QUOTE_PRECEDES_NEW_PROJECTION_LOCK")
    if market_capture < oldest_quote:
        reasons.append("MARKET_CAPTURE_PRECEDES_QUOTE")
    if market_receipt["complete_posted_ladder_verified"] is not True:
        reasons.append("MARKET_LADDER_INCOMPLETE")
    if market_receipt["price_identity_verified"] is not True:
        reasons.append("MARKET_PRICE_IDENTITY_UNVERIFIED")

    ready=not reasons
    return {
        "mode":"ROLE_MARKET_REVALIDATION_COMPLETION",
        "status":"READY_FOR_FINAL_V7_QUALIFICATION" if ready else "HOLD",
        "reasons":reasons,
        "event_id":plan["event_id"],
        "replacement_decision_version":plan["replacement_decision_version"],
        "projection_locked_at":rerun_receipt["projection_locked_at"],
        "market_captured_at":market_receipt["captured_at"],
        "ready_for_final_v7_qualification":ready,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
        "note":"This state does not bypass calibrated probability, EV, scenario, source, or final live V7 gates.",
    }
