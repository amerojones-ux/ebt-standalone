"""Synthetic tests for immutable role/market revalidation orchestration."""
import unittest

from extensions.revalidation_orchestrator import (
    assess_revalidation_completion,
    plan_event_revalidation,
    role_state_from_nba_injury,
)

A="a"*64
B="b"*64
C="c"*64
D="d"*64
E="e"*64
F="f"*64
EVENT_KEY="2026-11-07|AAA@BBB"


def prior():
    return {
        "decision_id":"D-1","decision_version":1,"event_id":"E-1",
        "event_key":EVENT_KEY,"model_version":"M-1",
        "projection_locked_at":"2026-11-07T12:00:00Z",
        "role_evidence_sha256":A,"market_snapshot_sha256":D,
        "market_captured_at":"2026-11-07T12:05:00Z",
        "decision_status":"HOLD",
    }


def current(*,role_hash=B,available_at="2026-11-07T12:10:00Z",
            gate="FOUND",rerun=True,hold=False,changes=1):
    return {
        "event_id":"E-1","event_key":EVENT_KEY,
        "role_evidence_sha256":role_hash,
        "role_evidence_available_at":available_at,
        "game_gate_status":gate,"full_rerun_required":rerun,
        "hold_for_confirmation":hold,"change_count":changes,
        "affected_player_ids":["P-1"] if changes else [],
    }


def role_gate(status="FOUND",role_hash=B,available_at="2026-11-07T12:10:00Z"):
    return {
        "event_id":"E-1","event_key":EVENT_KEY,"status":status,
        "role_evidence_sha256":role_hash,"available_at":available_at,
    }


def rerun_receipt(*,role_hash=B,lock="2026-11-07T12:20:00Z",trials=100000):
    run={"trials":trials,"input_sha256":D,"code_sha256":E}
    return {
        "event_id":"E-1","decision_version":2,"model_version":"M-2",
        "role_evidence_sha256":role_hash,"projection_sha256":C,
        "projection_locked_at":lock,
        "mc_runs":{
            "baseline":dict(run),"adversarial":dict(run),"scenario":dict(run)
        },
    }


def market_receipt(*,capture="2026-11-07T12:30:00Z",
                   quote="2026-11-07T12:25:00Z",complete=True,identity=True):
    return {
        "event_id":"E-1","market_snapshot_sha256":F,
        "captured_at":capture,"oldest_quote_at":quote,
        "complete_posted_ladder_verified":complete,
        "price_identity_verified":identity,
    }


class RevalidationOrchestratorTests(unittest.TestCase):
    def test_new_material_role_state_revokes_prior_decision(self):
        out=plan_event_revalidation(prior(),current())
        self.assertTrue(out["prior_decision_revoked"])
        self.assertTrue(out["prior_market_snapshot_revoked"])
        self.assertEqual(out["replacement_decision_version"],2)
        self.assertIn("REBUILD_INDEPENDENT_PROJECTION",out["required_steps"])
        self.assertEqual(out["wager_status"],"NOT APPROVED")

    def test_role_gate_hold_revokes_even_without_material_change(self):
        out=plan_event_revalidation(
            prior(),current(gate="HOLD",rerun=False,hold=True,changes=0))
        self.assertTrue(out["prior_decision_revoked"])
        self.assertEqual(out["status"],"HOLD_ROLE_CONFIRMATION")

    def test_nonmaterial_role_refresh_does_not_revoke(self):
        out=plan_event_revalidation(
            prior(),current(rerun=False,hold=False,changes=0))
        self.assertFalse(out["prior_decision_revoked"])
        self.assertEqual(out["replacement_decision_version"],1)
        self.assertIn("NONMATERIAL_ROLE_EVIDENCE_REFRESH",out["reasons"])

    def test_material_change_same_evidence_hash_is_provenance_conflict(self):
        out=plan_event_revalidation(prior(),current(role_hash=A))
        self.assertTrue(out["provenance_conflict"])
        self.assertEqual(out["status"],"HOLD_PROVENANCE_CONFLICT")

    def test_material_change_not_newer_than_prior_lock_is_provenance_conflict(self):
        out=plan_event_revalidation(
            prior(),current(available_at="2026-11-07T11:59:00Z"))
        self.assertTrue(out["provenance_conflict"])

    def test_complete_rebuild_order_can_reach_final_qualification_handoff(self):
        plan=plan_event_revalidation(prior(),current())
        out=assess_revalidation_completion(
            plan,current_role_gate=role_gate(),
            rerun_receipt=rerun_receipt(),
            market_receipt=market_receipt())
        self.assertTrue(out["ready_for_final_v7_qualification"])
        self.assertEqual(out["status"],"READY_FOR_FINAL_V7_QUALIFICATION")
        self.assertEqual(out["wager_status"],"NOT APPROVED")

    def test_incomplete_market_ladder_blocks_completion(self):
        plan=plan_event_revalidation(prior(),current())
        out=assess_revalidation_completion(
            plan,current_role_gate=role_gate(),
            rerun_receipt=rerun_receipt(),
            market_receipt=market_receipt(complete=False))
        self.assertFalse(out["ready_for_final_v7_qualification"])
        self.assertIn("MARKET_LADDER_INCOMPLETE",out["reasons"])

    def test_market_quote_before_projection_lock_blocks_completion(self):
        plan=plan_event_revalidation(prior(),current())
        out=assess_revalidation_completion(
            plan,current_role_gate=role_gate(),
            rerun_receipt=rerun_receipt(),
            market_receipt=market_receipt(quote="2026-11-07T12:19:00Z"))
        self.assertIn("MARKET_QUOTE_PRECEDES_NEW_PROJECTION_LOCK",out["reasons"])

    def test_under_100k_mc_blocks_completion(self):
        plan=plan_event_revalidation(prior(),current())
        out=assess_revalidation_completion(
            plan,current_role_gate=role_gate(),
            rerun_receipt=rerun_receipt(trials=99999),
            market_receipt=market_receipt())
        self.assertTrue(any(x.startswith("MC_") for x in out["reasons"]))
        self.assertFalse(out["ready_for_final_v7_qualification"])

    def test_role_state_changed_again_blocks_completion(self):
        plan=plan_event_revalidation(prior(),current())
        out=assess_revalidation_completion(
            plan,current_role_gate=role_gate(role_hash=C),
            rerun_receipt=rerun_receipt(role_hash=C),
            market_receipt=market_receipt())
        self.assertIn("ROLE_EVIDENCE_CHANGED_AGAIN",out["reasons"])

    def test_tampered_plan_is_rejected_by_hash(self):
        plan=plan_event_revalidation(prior(),current())
        plan=dict(plan)
        plan["replacement_decision_version"]=99
        with self.assertRaises(ValueError):
            assess_revalidation_completion(
                plan,current_role_gate=role_gate(),
                rerun_receipt=rerun_receipt(),
                market_receipt=market_receipt())

    def test_nba_injury_bridge_is_scoped_to_one_event(self):
        report={
            "rows":[
                {
                    "event_key":EVENT_KEY,"event_id":"E-1","team_id":"T-1",
                    "player_id":"P-1","row_type":"PLAYER_STATUS",
                    "current_status":"Out","reason":"Synthetic","submission_status":"SUBMITTED",
                    "report_time_utc":"2026-11-07T12:10:00Z",
                    "captured_at":"2026-11-07T12:11:00Z",
                },
                {
                    "event_key":EVENT_KEY,"event_id":"E-1","team_id":"T-2",
                    "player_id":"P-2","row_type":"PLAYER_STATUS",
                    "current_status":"Probable","reason":"Synthetic2","submission_status":"SUBMITTED",
                    "report_time_utc":"2026-11-07T12:10:00Z",
                    "captured_at":"2026-11-07T12:11:00Z",
                },
            ]
        }
        diff={
            "changes":[
                {"kind":"PLAYER_STATUS_CHANGE","key":[EVENT_KEY,"T-1","P-1"]},
                {"kind":"PLAYER_REMOVED_REQUIRES_CONFIRMATION",
                 "key":["2026-11-07|CCC@DDD","T-3","P-3"]},
            ],
            "full_rerun_required":True,"hold_for_confirmation":True,
        }
        gate={"event_key":EVENT_KEY,"status":"FOUND"}
        out=role_state_from_nba_injury(report,diff,gate,event_key=EVENT_KEY)
        self.assertEqual(out["change_count"],1)
        self.assertEqual(out["affected_player_ids"],["P-1"])
        self.assertTrue(out["full_rerun_required"])
        self.assertFalse(out["hold_for_confirmation"])


if __name__=="__main__":
    unittest.main()
