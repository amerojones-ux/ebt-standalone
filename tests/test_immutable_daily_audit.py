"""Synthetic lifecycle tests for immutable daily Black Diamond audit."""
import json
import tempfile
import unittest
from pathlib import Path

from ebt_validation import record_hash
from extensions.immutable_daily_audit import (
    append_daily_audit_record,
    artifact_ref_from_receipt,
    summarize_daily_audit,
    validate_audit_payload,
    verify_artifact_ref,
    validate_daily_audit_chain,
)

ZERO="0"*64
A="a"*64
B="b"*64
C="c"*64
D="d"*64
E="e"*64
F="f"*64
G="1"*64
H="2"*64

EVENT_START="2026-11-07T20:00:00Z"
PREGAME="2026-11-07T18:00:00Z"
PREGAME2="2026-11-07T18:30:00Z"
FINAL="2026-11-07T23:00:00Z"
POSTGAME="2026-11-08T00:00:00Z"
AUDIT_DATE="2026-11-07"


def payload(record_type,data,*,effective=PREGAME,recorded=PREGAME,
            supersedes=None,event=True,audit_date=AUDIT_DATE):
    return {
        "schema_version":"1.0",
        "audit_date_ct":audit_date,
        "record_type":record_type,
        "subject_id":"SUBJECT-1",
        "event_id":"EVENT-1" if event else None,
        "event_start":EVENT_START if event else None,
        "effective_at":effective,
        "recorded_at":recorded,
        "supersedes_record_id":supersedes,
        "artifact_refs":[],
        "data":data,
    }


def decision(version=1,sha=A):
    return {
        "decision_id":"DEC-1",
        "decision_version":version,
        "market_key":"PLAYER_POINTS_GE_20",
        "verdict":"HOLD",
        "decision_sha256":sha,
    }


def settlement(version=1,reason=None):
    return {
        "decision_id":"DEC-1",
        "settlement_version":version,
        "settlement":"HIT",
        "actual":24,
        "official_result_verified":True,
        "result_source_sha256":F,
        "revision_reason":reason,
    }


def chain_record(record_id,payload_obj,previous):
    record={
        "id":record_id,
        "previous_sha256":previous,
        "payload":payload_obj,
    }
    record["sha256"]=record_hash(record)
    return record


class ImmutableDailyAuditTests(unittest.TestCase):
    def test_complete_lifecycle_is_valid_and_summarized(self):
        records=[]
        last=ZERO
        sequence=[
            ("SRC",payload("PREGAME_SOURCE_EVIDENCE",{
                "source_role":"A1_OFFICIAL_ROLE",
                "source_status":"FOUND",
                "evidence_sha256":A,
            })),
            ("MODEL",payload("PREGAME_MODEL_ARTIFACT",{
                "artifact_type":"BENEFICIARY_OPPORTUNITY_SHARE",
                "artifact_sha256":B,
                "status":"HOLD_RESEARCH",
            })),
            ("FORECAST",payload("PREGAME_FORECAST_LOCK",{
                "forecast_id":"F-1",
                "model_version":"M-1",
                "projection_sha256":C,
                "role_evidence_sha256":A,
                "forecast_status":"HOLD",
            })),
            ("DEC1",payload("PREGAME_DECISION",decision(1,D))),
            ("ROLE",payload("ROLE_REVALIDATION",{
                "prior_decision_id":"DEC-1",
                "replacement_decision_version":2,
                "plan_sha256":E,
                "status":"REVALIDATION_REQUIRED",
            },effective=PREGAME2,recorded=PREGAME2)),
            ("DEC2",payload("PREGAME_DECISION",decision(2,G),
                            effective=PREGAME2,recorded=PREGAME2,
                            supersedes="DEC1")),
            ("MARKET",payload("MARKET_SNAPSHOT",{
                "snapshot_sha256":H,
                "model_locked_at":"2026-11-07T18:20:00Z",
                "complete_posted_ladder_verified":True,
                "price_identity_verified":True,
                "source_status":"FOUND",
            },effective=PREGAME2,recorded=PREGAME2)),
            ("MC1",payload("MC_RECEIPT",{
                "purpose":"MC1_BASELINE","trials":100000,
                "input_sha256":A,"code_sha256":B,
            },effective=PREGAME2,recorded=PREGAME2)),
            ("MC2",payload("MC_RECEIPT",{
                "purpose":"MC2_ADVERSARIAL","trials":100000,
                "input_sha256":C,"code_sha256":B,
            },effective=PREGAME2,recorded=PREGAME2)),
            ("MC3",payload("MC_RECEIPT",{
                "purpose":"MC3_SCENARIO_CORRELATION","trials":100000,
                "input_sha256":D,"code_sha256":B,
            },effective=PREGAME2,recorded=PREGAME2)),
            ("SHADOW",payload("SHADOW_CANDIDATE",{
                "candidate_id":"CAND-2",
                "lane":"TAIL_VALUE_RESEARCH",
                "reason":"Below live approval threshold",
            },effective=PREGAME2,recorded=PREGAME2)),
            ("REJECT",payload("REJECTED_CANDIDATE",{
                "candidate_id":"CAND-3",
                "reason":"Role uncertainty",
                "kill_switch":"UNCONFIRMED_MINUTES",
            },effective=PREGAME2,recorded=PREGAME2)),
            ("SET1",payload("SETTLEMENT",settlement(1),
                            effective=FINAL,recorded=FINAL)),
            ("POST",payload("POSTGAME_REVERSE_AUDIT",{
                "decision_id":"DEC-1",
                "settlement_record_id":"SET1",
                "identifiability":"PRE_GAME_IDENTIFIABLE",
                "variance_class":"STRUCTURAL_CANDIDATE",
                "mechanism":"Verified role expansion persisted.",
                "failure_mechanism":"NONE_HIT",
                "pregame_evidence_eligible":False,
            },effective=POSTGAME,recorded=POSTGAME)),
        ]
        for record_id,pay in sequence:
            rec=chain_record(record_id,pay,last)
            records.append(rec)
            last=rec["sha256"]

        self.assertEqual(validate_daily_audit_chain(records),last)
        summary=summarize_daily_audit(records)
        self.assertEqual(summary["decision_count"],1)
        self.assertEqual(summary["settled_decision_count"],1)
        self.assertEqual(summary["unsettled_decision_ids"],[])
        self.assertTrue(summary["pregame_records_immutable"])
        self.assertFalse(summary["model_weights_changed_by_audit"])

    def test_engine_receipt_artifact_reference_is_canonical_and_tamper_evident(self):
        receipt={
            "mode":"OFFLINE_BENEFICIARY_OPPORTUNITY_REALLOCATION",
            "status":"HOLD",
            "players":[{"player_id":"P1","final_expected_units":"34"}],
        }
        ref=artifact_ref_from_receipt("BENEFICIARY_REALLOCATION",receipt)
        self.assertEqual(len(ref["sha256"]),64)
        self.assertTrue(verify_artifact_ref(ref,receipt))
        tampered={**receipt,"status":"APPROVED"}
        with self.assertRaises(ValueError):
            verify_artifact_ref(ref,tampered)

    def test_pregame_record_after_start_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_audit_payload(payload(
                "PREGAME_MODEL_ARTIFACT",
                {"artifact_type":"X","artifact_sha256":A,"status":"HOLD"},
                effective=FINAL,recorded=FINAL))

    def test_final_record_before_start_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_audit_payload(payload(
                "SETTLEMENT",settlement(),
                effective=PREGAME,recorded=PREGAME))

    def test_market_snapshot_cannot_predate_model_lock(self):
        rec=chain_record("M",payload("MARKET_SNAPSHOT",{
            "snapshot_sha256":A,
            "model_locked_at":"2026-11-07T18:45:00Z",
            "complete_posted_ladder_verified":True,
            "price_identity_verified":True,
            "source_status":"FOUND",
        },effective=PREGAME2,recorded=PREGAME2),ZERO)
        with self.assertRaises(ValueError):
            validate_daily_audit_chain([rec])

    def test_mc_receipt_requires_100k(self):
        with self.assertRaises(ValueError):
            validate_audit_payload(payload("MC_RECEIPT",{
                "purpose":"MC1_BASELINE","trials":99999,
                "input_sha256":A,"code_sha256":B,
            }))

    def test_role_revalidation_requires_prior_decision(self):
        rec=chain_record("ROLE",payload("ROLE_REVALIDATION",{
            "prior_decision_id":"MISSING",
            "replacement_decision_version":2,
            "plan_sha256":A,
            "status":"REVALIDATION_REQUIRED",
        }),ZERO)
        with self.assertRaises(ValueError):
            validate_daily_audit_chain([rec])

    def test_decision_revision_must_supersede_latest_and_increment(self):
        one=chain_record("D1",payload("PREGAME_DECISION",decision(1,A)),ZERO)
        two=chain_record("D2",payload(
            "PREGAME_DECISION",decision(3,B),
            supersedes="D1",effective=PREGAME2,recorded=PREGAME2),one["sha256"])
        with self.assertRaises(ValueError):
            validate_daily_audit_chain([one,two])

    def test_settlement_requires_prior_decision_and_verified_official_result(self):
        with self.assertRaises(ValueError):
            validate_audit_payload(payload(
                "SETTLEMENT",
                {**settlement(),"official_result_verified":False},
                effective=FINAL,recorded=FINAL))
        s=chain_record("S",payload(
            "SETTLEMENT",settlement(),effective=FINAL,recorded=FINAL),ZERO)
        with self.assertRaises(ValueError):
            validate_daily_audit_chain([s])

    def test_settlement_revision_is_append_only_and_requires_reason(self):
        d=chain_record("D1",payload("PREGAME_DECISION",decision()),ZERO)
        s1=chain_record("S1",payload(
            "SETTLEMENT",settlement(1),effective=FINAL,recorded=FINAL),d["sha256"])
        s2=chain_record("S2",payload(
            "SETTLEMENT",settlement(2,None),
            effective="2026-11-08T01:00:00Z",
            recorded="2026-11-08T01:00:00Z",
            supersedes="S1"),s1["sha256"])
        with self.assertRaises(ValueError):
            validate_daily_audit_chain([d,s1,s2])

        corrected=payload(
            "SETTLEMENT",settlement(2,"Official stat correction"),
            effective="2026-11-08T01:00:00Z",
            recorded="2026-11-08T01:00:00Z",
            supersedes="S1")
        s2=chain_record("S2",corrected,s1["sha256"])
        self.assertEqual(
            validate_daily_audit_chain([d,s1,s2]),s2["sha256"])

    def test_postgame_audit_must_reference_matching_settlement(self):
        d=chain_record("D1",payload("PREGAME_DECISION",decision()),ZERO)
        s=chain_record("S1",payload(
            "SETTLEMENT",settlement(),effective=FINAL,recorded=FINAL),d["sha256"])
        p=payload("POSTGAME_REVERSE_AUDIT",{
            "decision_id":"OTHER",
            "settlement_record_id":"S1",
            "identifiability":"POSTGAME_ONLY",
            "variance_class":"RANDOM_OR_UNRESOLVED",
            "mechanism":"Late random event.",
            "failure_mechanism":"RANDOM_VARIANCE",
            "pregame_evidence_eligible":False,
        },effective=POSTGAME,recorded=POSTGAME)
        r=chain_record("P1",p,s["sha256"])
        with self.assertRaises(ValueError):
            validate_daily_audit_chain([d,s,r])

    def test_postgame_record_can_never_be_marked_as_pregame_evidence(self):
        with self.assertRaises(ValueError):
            validate_audit_payload(payload("POSTGAME_REVERSE_AUDIT",{
                "decision_id":"DEC-1",
                "settlement_record_id":"S1",
                "identifiability":"PRE_GAME_IDENTIFIABLE",
                "variance_class":"STRUCTURAL_CANDIDATE",
                "mechanism":"Mechanism",
                "failure_mechanism":"NONE",
                "pregame_evidence_eligible":True,
            },effective=POSTGAME,recorded=POSTGAME))

    def test_review_records_cannot_claim_event_or_model_mutation(self):
        with self.assertRaises(ValueError):
            validate_audit_payload(payload(
                "CALIBRATION_REVIEW",{
                    "review_sha256":A,
                    "status":"ELIGIBLE",
                    "calibration_verified":True,
                    "model_promotion_applied":False,
                },event=False,audit_date="2026-11-07"))
        with self.assertRaises(ValueError):
            validate_audit_payload(payload(
                "LEARNING_REVIEW",{
                    "review_sha256":B,
                    "status":"ELIGIBLE",
                    "weight_change_applied":True,
                    "threshold_change_applied":False,
                    "model_promotion_applied":False,
                },event=False,audit_date="2026-11-07"))

    def test_review_record_cannot_claim_event_identity(self):
        p=payload("LEARNING_REVIEW",{
            "review_sha256":A,
            "status":"HOLD",
            "weight_change_applied":False,
            "threshold_change_applied":False,
            "model_promotion_applied":False,
        })
        with self.assertRaises(ValueError):
            validate_audit_payload(p)

    def test_central_audit_date_must_match_event_date(self):
        with self.assertRaises(ValueError):
            validate_audit_payload(payload(
                "PREGAME_MODEL_ARTIFACT",
                {"artifact_type":"X","artifact_sha256":A,"status":"HOLD"},
                audit_date="2026-11-08"))

    def test_hash_chain_tampering_is_detected(self):
        d=chain_record("D1",payload("PREGAME_DECISION",decision()),ZERO)
        d["payload"]["data"]["market_key"]="TAMPERED"
        with self.assertRaises(ValueError):
            validate_daily_audit_chain([d])

    def test_atomic_append_rejects_stale_writer_and_duplicate_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"audit.jsonl"
            p1=payload("PREGAME_DECISION",decision())
            last=append_daily_audit_record(
                path,"D1",p1,expected_last_sha256=ZERO)
            self.assertEqual(len(last),64)
            with self.assertRaises(ValueError):
                append_daily_audit_record(
                    path,"X",payload("SHADOW_CANDIDATE",{
                        "candidate_id":"C","lane":"SHADOW","reason":"Test",
                    }),expected_last_sha256=ZERO)
            with self.assertRaises(ValueError):
                append_daily_audit_record(
                    path,"D1",payload("SHADOW_CANDIDATE",{
                        "candidate_id":"C","lane":"SHADOW","reason":"Test",
                    }),expected_last_sha256=last)

    def test_atomic_append_validates_references_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"audit.jsonl"
            bad=payload("ROLE_REVALIDATION",{
                "prior_decision_id":"MISSING",
                "replacement_decision_version":2,
                "plan_sha256":A,
                "status":"REVALIDATION_REQUIRED",
            })
            with self.assertRaises(ValueError):
                append_daily_audit_record(
                    path,"R1",bad,expected_last_sha256=ZERO)
            self.assertEqual(path.read_text() if path.exists() else "","")


if __name__=="__main__":
    unittest.main()
