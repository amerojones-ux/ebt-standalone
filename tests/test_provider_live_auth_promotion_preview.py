import copy
import json
import unittest
from unittest.mock import patch

from apisports_status_receipt import build_receipt
from provider_attested_review_decision import sign_attested_review_decision
from provider_evidence_review_decision import review_candidate
from provider_live_auth_promotion_preview import (
    build_live_auth_promotion_preview,
)
from provider_receipt_review_candidate import (
    bind_attestation_verification,
    build_review_candidate,
)
from provider_live_request_plan import request_plan_sha256

COMMIT="a"*40
RUN="12345"
ARTIFACT="d"*64
MARKER="e"*64
REQUEST_PLAN=request_plan_sha256("API-Sports")
REPO="amerojones-ux/ebt-standalone"
ATTESTATION_ID="attestation-123"
ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+ATTESTATION_ID
SIGNER=".github/workflows/apisports-status-probe.yml"
REVIEWER="github:reviewer#123"
REVIEW_RUN="777"
REVIEW_COMMIT="f"*40
REVIEW_DECISION_FILE_SHA="1"*64
REVIEW_MARKER_FILE_SHA="2"*64
REVIEW_ATTESTATION_ID="review-attestation-123"
REVIEW_ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+REVIEW_ATTESTATION_ID
REVIEW_SIGNER=".github/workflows/provider-live-auth-evidence-review.yml"
NOW="2026-11-02T21:00:00+00:00"
REVIEWED="2026-11-02T20:59:00+00:00"

def readiness():
    with open("config/provider_readiness.json",encoding="utf-8") as handle:
        return json.load(handle)

def ledger():
    with open("config/provider_evidence.json",encoding="utf-8") as handle:
        return json.load(handle)

def raw_decision():
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:58:00+00:00",COMMIT,RUN
    )
    pending=build_review_candidate(
        receipt,
        artifact_sha256=ARTIFACT,
        expected_run_id=RUN,
        expected_commit=COMMIT,
    )
    candidate=bind_attestation_verification(
        pending,
        marker_sha256=MARKER,
        request_plan_sha256=REQUEST_PLAN,
        source_repository=REPO,
        attestation_id=ATTESTATION_ID,
        attestation_url=ATTESTATION_URL,
        signer_workflow=SIGNER,
        **EXECUTION_KWARGS,
    )
    return review_candidate(
        candidate,
        decision="APPROVE",
        reviewer=REVIEWER,
        reviewed_at=REVIEWED,
        trusted_now=NOW,
    )

def attested_decision():
    raw=raw_decision()
    proposal=copy.deepcopy(raw["ledger_record_proposal"])
    proposal.update({
        "review_repository":REPO,
        "review_workflow_run_id":REVIEW_RUN,
        "review_source_commit":REVIEW_COMMIT,
        "review_github_metadata_match":True,
        "review_decision_sha256":raw["decision_sha256"],
        "review_decision_file_sha256":REVIEW_DECISION_FILE_SHA,
        "review_attestation_marker_sha256":REVIEW_MARKER_FILE_SHA,
        "review_attestation_id":REVIEW_ATTESTATION_ID,
        "review_attestation_url":REVIEW_ATTESTATION_URL,
        "review_signer_workflow":REVIEW_SIGNER,
    })
    return sign_attested_review_decision({
        "subject":raw["subject"],
        "claim":raw["claim"],
        "decision":raw["decision"],
        "reviewer":raw["reviewer"],
        "reviewed_at":raw["reviewed_at"],
        "candidate_sha256":raw["candidate_sha256"],
        "decision_sha256":raw["decision_sha256"],
        "attested_status":"ATTESTED_APPROVED_FOR_MANUAL_LEDGER_REVIEW",
        "review_repository":REPO,
        "review_workflow_run_id":REVIEW_RUN,
        "review_source_commit":REVIEW_COMMIT,
        "review_github_metadata_match":True,
        "review_decision_file_sha256":REVIEW_DECISION_FILE_SHA,
        "review_attestation_marker_sha256":REVIEW_MARKER_FILE_SHA,
        "review_attestation_id":REVIEW_ATTESTATION_ID,
        "review_attestation_url":REVIEW_ATTESTATION_URL,
        "review_signer_workflow":REVIEW_SIGNER,
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
        "ledger_record_proposal":proposal,
    })

EXECUTION_KWARGS={
    "execution_intent_sha256":"3"*64,
    "execution_intent_file_sha256":"4"*64,
    "execution_intent_marker_sha256":"5"*64,
    "execution_intent_bundle_sha256":"6"*64,
    "execution_intent_attestation_id":"intent-attestation-123",
    "execution_intent_attestation_url":
        "https://github.com/"+REPO+"/attestations/intent-attestation-123",
    "execution_actor":"amerojones-ux",
    "execution_actor_id":"262097315",
    "execution_max_requests":1,
}
class ProviderLiveAuthPromotionPreviewTests(unittest.TestCase):
    def test_preview_sets_only_live_auth_and_stays_safe_hold(self):
        original=readiness()
        result=build_live_auth_promotion_preview(
            original,ledger(),attested_decision(),trusted_now=NOW
        )
        self.assertEqual(
            result["preview_status"],
            "VALID_LIVE_AUTH_PROMOTION_PREVIEW",
        )
        self.assertEqual(result["provider"],"API-Sports")
        self.assertEqual(result["global_provider_gate"],"SAFE_HOLD")
        self.assertFalse(result["ledger_write_permitted"])
        self.assertFalse(result["readiness_write_permitted"])
        self.assertFalse(result["forecast_activation_permitted"])
        self.assertEqual(len(result["preview_sha256"]),64)

        before=next(
            x for x in original["providers"] if x["name"]=="API-Sports"
        )
        after=next(
            x for x in result["preview_readiness"]["providers"]
            if x["name"]=="API-Sports"
        )
        self.assertFalse(before["live_auth_verified"])
        self.assertTrue(after["live_auth_verified"])
        for key,value in before.items():
            if key!="live_auth_verified":
                self.assertEqual(after[key],value)

        self.assertFalse(original["forecast_enabled"])
        self.assertFalse(result["preview_readiness"]["forecast_enabled"])
        self.assertEqual(original["required_providers"],[])
        self.assertEqual(result["preview_readiness"]["required_providers"],[])

    def test_raw_decision_cannot_promote(self):
        with self.assertRaises(ValueError):
            build_live_auth_promotion_preview(
                readiness(),ledger(),raw_decision(),trusted_now=NOW
            )

    def test_original_inputs_are_not_mutated(self):
        r=readiness()
        l=ledger()
        r_before=copy.deepcopy(r)
        l_before=copy.deepcopy(l)
        build_live_auth_promotion_preview(
            r,l,attested_decision(),trusted_now=NOW
        )
        self.assertEqual(r,r_before)
        self.assertEqual(l,l_before)

    def test_existing_live_auth_true_cannot_be_overwritten(self):
        r=readiness()
        for entry in r["providers"]:
            if entry["name"]=="API-Sports":
                entry["live_auth_verified"]=True
        with self.assertRaises(ValueError):
            build_live_auth_promotion_preview(
                r,ledger(),attested_decision(),trusted_now=NOW
            )

    def test_forced_non_hold_activation_result_is_rejected(self):
        with patch(
            "provider_live_auth_promotion_preview.status",
            return_value="ELIGIBLE_FOR_MANUAL_ACTIVATION_REVIEW",
        ):
            with self.assertRaises(ValueError):
                build_live_auth_promotion_preview(
                    readiness(),ledger(),attested_decision(),trusted_now=NOW
                )

    def test_preview_refuses_activation_boundary_crossing(self):
        r=readiness()
        r["required_providers"]=["API-Sports"]
        r["model_gates"]={
            "source_provenance_verified":True,
            "roster_injury_identity_verified":True,
            "historical_calibration_verified":True,
            "joint_dependence_verified":True,
        }
        for entry in r["providers"]:
            if entry["name"]=="API-Sports":
                entry["entitlement_verified"]=True
                entry["identity_verified"]=True
                entry["freshness_verified"]=True
                entry["model_evidence_allowed"]=True

        with self.assertRaises(ValueError):
            build_live_auth_promotion_preview(
                r,ledger(),attested_decision(),trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
