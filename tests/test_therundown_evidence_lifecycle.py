import copy
import json
import unittest

from therundown_probe_receipt import build_receipt
from provider_attested_review_decision import (
    sign_attested_review_decision,
    verify_attested_review_decision,
)
from provider_evidence_review_decision import review_candidate
from provider_live_auth_promotion_preview import build_live_auth_promotion_preview
from provider_live_request_plan import request_plan_sha256
from provider_receipt_review_candidate import (
    bind_attestation_verification,
    build_review_candidate,
)

COMMIT="a"*40
INTENT_SHA="3"*64
RUN="12345"
ARTIFACT="d"*64
MARKER="e"*64
REPO="amerojones-ux/ebt-standalone"
ATTESTATION_ID="attestation-123"
ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+ATTESTATION_ID
SIGNER=".github/workflows/therundown-live-probe.yml"
REVIEWER="github:reviewer#123"
REVIEW_RUN="777"
REVIEW_COMMIT="f"*40
REVIEW_DECISION_FILE_SHA="1"*64
REVIEW_MARKER_FILE_SHA="2"*64
REVIEW_ATTESTATION_ID="review-attestation-123"
REVIEW_ATTESTATION_URL=(
    "https://github.com/"+REPO+"/attestations/"+REVIEW_ATTESTATION_ID
)
REVIEW_SIGNER=".github/workflows/provider-live-auth-evidence-review.yml"
NOW="2026-11-04T01:00:00+00:00"
REVIEWED="2026-11-04T00:59:00+00:00"

EXECUTION_KWARGS={
    "execution_intent_sha256":INTENT_SHA,
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

def readiness():
    from tests.provider_test_fixtures import readiness as synthetic_fixture
    return synthetic_fixture()

def ledger():
    from tests.provider_test_fixtures import ledger as synthetic_fixture
    return synthetic_fixture()

def attested_decision():
    receipt=build_receipt(
        {
            "status":"PASS",
            "category":"authenticated_zero_datapoint_sample_json",
        },
        "2026-11-04T00:58:00+00:00",
        COMMIT,
        RUN,
        INTENT_SHA,
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
        request_plan_sha256=request_plan_sha256("TheRundown"),
        source_repository=REPO,
        attestation_id=ATTESTATION_ID,
        attestation_url=ATTESTATION_URL,
        signer_workflow=SIGNER,
        **EXECUTION_KWARGS,
    )
    raw=review_candidate(
        candidate,
        decision="APPROVE",
        reviewer=REVIEWER,
        reviewed_at=REVIEWED,
        trusted_now=NOW,
    )
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

class TheRundownEvidenceLifecycleTests(unittest.TestCase):
    def test_sample_auth_evidence_can_preview_live_auth_only(self):
        decision=attested_decision()
        self.assertTrue(verify_attested_review_decision(decision))
        result=build_live_auth_promotion_preview(
            readiness(),
            ledger(),
            decision,
            trusted_now=NOW,
        )
        self.assertEqual(
            result["preview_status"],
            "VALID_LIVE_AUTH_PROMOTION_PREVIEW",
        )
        self.assertEqual(result["provider"],"TheRundown")
        self.assertEqual(result["global_provider_gate"],"SAFE_HOLD")
        self.assertFalse(result["ledger_write_permitted"])
        self.assertFalse(result["readiness_write_permitted"])
        self.assertFalse(result["forecast_activation_permitted"])
        self.assertFalse(result["preview_readiness"]["forecast_enabled"])
        self.assertFalse(result["preview_readiness"]["network_autorun_enabled"])
        target=next(
            x for x in result["preview_readiness"]["providers"]
            if x["name"]=="TheRundown"
        )
        self.assertTrue(target["live_auth_verified"])
        self.assertFalse(target["entitlement_verified"])
        self.assertFalse(target["identity_verified"])
        self.assertFalse(target["freshness_verified"])
        self.assertFalse(target["model_evidence_allowed"])
        record=next(
            x for x in result["preview_ledger"]["providers"]
            if x["name"]=="TheRundown"
        )["evidence"]
        self.assertIsNotNone(record["live_auth_verified"])
        self.assertIsNone(record["model_evidence_allowed"])

if __name__=="__main__":
    unittest.main()
