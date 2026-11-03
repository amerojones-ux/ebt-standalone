import unittest

from apisports_status_receipt import build_receipt as build_apisports
from provider_receipt_review_candidate import build_review_candidate, bind_attestation_verification
from provider_evidence_review_decision import review_candidate, verify_candidate
from provider_readiness_evidence_gate import validate_record
from provider_live_request_plan import request_plan_sha256

COMMIT="a"*40
INTENT_SHA="3"*64
RUN="12345"
ARTIFACT="d"*64
MARKER="e"*64
REQUEST_PLAN=request_plan_sha256("API-Sports")
REPO="amerojones-ux/ebt-standalone"
ATTESTATION_ID="attestation-123"
ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+ATTESTATION_ID
SIGNER=".github/workflows/apisports-status-probe.yml"
NOW="2026-11-02T21:00:00+00:00"
REVIEWED="2026-11-02T20:59:00+00:00"


_raw_build_apisports=build_apisports

def build_apisports(*args,**kwargs):
    kwargs.setdefault("execution_intent_sha256",INTENT_SHA)
    return _raw_build_apisports(*args,**kwargs)

def candidate():
    receipt=build_apisports(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:58:00+00:00",COMMIT,RUN
    )
    pending=build_review_candidate(
        receipt,artifact_sha256=ARTIFACT,
        expected_run_id=RUN,expected_commit=COMMIT
    )
    return bind_attestation_verification(
        pending,
        marker_sha256=MARKER,
        request_plan_sha256=REQUEST_PLAN,
        source_repository=REPO,
        attestation_id=ATTESTATION_ID,
        attestation_url=ATTESTATION_URL,
        signer_workflow=SIGNER,
        **EXECUTION_KWARGS,
    )

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
class ProviderEvidenceReviewDecisionTests(unittest.TestCase):
    def test_candidate_checksum_verifies(self):
        self.assertTrue(verify_candidate(candidate()))

    def test_pending_attestation_candidate_cannot_be_reviewed(self):
        receipt=build_apisports(
            {"status":"PASS","category":"authenticated_status_schema"},
            "2026-11-02T20:58:00+00:00",COMMIT,RUN
        )
        pending=build_review_candidate(
            receipt,artifact_sha256=ARTIFACT,
            expected_run_id=RUN,expected_commit=COMMIT
        )
        self.assertFalse(verify_candidate(pending))
        with self.assertRaises(ValueError):
            review_candidate(
                pending,decision="APPROVE",reviewer="github:reviewer#123",
                reviewed_at=REVIEWED,trusted_now=NOW
            )

    def test_unsupported_provider_candidate_fails(self):
        c=candidate()
        c["provider"]="Unsupported"
        c["subject"]="Unsupported"
        import hashlib, json
        body={k:v for k,v in c.items() if k!="candidate_sha256"}
        c["candidate_sha256"]=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest()
        self.assertFalse(verify_candidate(c))

    def test_candidate_mutation_fails(self):
        c=candidate()
        c["provider"]="WeatherAPI"
        self.assertFalse(verify_candidate(c))

    def test_approve_emits_proposal_pending_review_attestation(self):
        r=review_candidate(
            candidate(),decision="APPROVE",reviewer="github:reviewer#123",
            reviewed_at=REVIEWED,trusted_now=NOW
        )
        self.assertEqual(r["proposal_status"],"APPROVED_FOR_MANUAL_LEDGER_REVIEW")
        self.assertEqual(r["ledger_record_proposal"]["status"],"VERIFIED")
        self.assertEqual(r["ledger_record_proposal"]["subject"],"API-Sports")
        self.assertEqual(r["ledger_record_proposal"]["claim"],"live_auth_verified")
        self.assertEqual(r["ledger_record_proposal"]["source_repository"],REPO)
        self.assertEqual(r["ledger_record_proposal"]["attestation_id"],ATTESTATION_ID)
        self.assertEqual(r["ledger_record_proposal"]["attestation_url"],ATTESTATION_URL)
        self.assertEqual(r["ledger_record_proposal"]["signer_workflow"],SIGNER)
        self.assertEqual(r["ledger_record_proposal"]["attestation_marker_sha256"],MARKER)
        self.assertIs(
            r["ledger_record_proposal"]["execution_intent_verified"],True
        )
        self.assertEqual(
            r["ledger_record_proposal"]["execution_intent_sha256"],
            EXECUTION_KWARGS["execution_intent_sha256"],
        )
        self.assertEqual(
            r["ledger_record_proposal"]["execution_actor"],
            EXECUTION_KWARGS["execution_actor"],
        )
        self.assertEqual(
            r["ledger_record_proposal"]["execution_max_requests"],1
        )
        self.assertFalse(r["ledger_mutation_permitted"])
        self.assertFalse(r["readiness_mutation_permitted"])
        self.assertFalse(r["forecast_activation_permitted"])
        errors=validate_record(
            r["ledger_record_proposal"],
            subject="API-Sports",
            claim="live_auth_verified",
            trusted_now=NOW,
        )
        self.assertTrue(errors)
        self.assertTrue(any("review_" in error or "reviewer" in error for error in errors))

    def test_reject_emits_no_ledger_record(self):
        r=review_candidate(
            candidate(),decision="REJECT",reviewer="github:reviewer#123",
            reviewed_at=REVIEWED,trusted_now=NOW
        )
        self.assertEqual(r["proposal_status"],"REJECTED")
        self.assertIsNone(r["ledger_record_proposal"])

    def test_future_review_rejected(self):
        with self.assertRaises(ValueError):
            review_candidate(
                candidate(),decision="APPROVE",reviewer="github:reviewer#123",
                reviewed_at="2026-11-02T22:00:00+00:00",trusted_now=NOW
            )

    def test_blank_reviewer_rejected(self):
        with self.assertRaises(ValueError):
            review_candidate(
                candidate(),decision="APPROVE",reviewer=" ",
                reviewed_at=REVIEWED,trusted_now=NOW
            )

    def test_invalid_decision_rejected(self):
        with self.assertRaises(ValueError):
            review_candidate(
                candidate(),decision="AUTO",reviewer="github:reviewer#123",
                reviewed_at=REVIEWED,trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
