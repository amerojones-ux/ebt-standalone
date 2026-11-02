import unittest

from apisports_status_receipt import build_receipt as build_apisports
from provider_receipt_review_candidate import build_review_candidate
from provider_evidence_review_decision import review_candidate, verify_candidate
from provider_readiness_evidence_gate import validate_record

COMMIT="a"*40
RUN="12345"
NOW="2026-11-02T21:00:00+00:00"
REVIEWED="2026-11-02T20:59:00+00:00"

def candidate():
    receipt=build_apisports(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:58:00+00:00",COMMIT,RUN
    )
    return build_review_candidate(receipt)

class ProviderEvidenceReviewDecisionTests(unittest.TestCase):
    def test_candidate_checksum_verifies(self):
        self.assertTrue(verify_candidate(candidate()))

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

    def test_approve_emits_manual_ledger_proposal_only(self):
        r=review_candidate(
            candidate(),decision="APPROVE",reviewer="authorized-reviewer",
            reviewed_at=REVIEWED,trusted_now=NOW
        )
        self.assertEqual(r["proposal_status"],"APPROVED_FOR_MANUAL_LEDGER_REVIEW")
        self.assertEqual(r["ledger_record_proposal"]["status"],"VERIFIED")
        self.assertEqual(r["ledger_record_proposal"]["subject"],"API-Sports")
        self.assertEqual(r["ledger_record_proposal"]["claim"],"live_auth_verified")
        self.assertFalse(r["ledger_mutation_permitted"])
        self.assertFalse(r["readiness_mutation_permitted"])
        self.assertFalse(r["forecast_activation_permitted"])
        self.assertEqual(
            validate_record(
                r["ledger_record_proposal"],
                subject="API-Sports",
                claim="live_auth_verified",
                trusted_now=NOW,
            ),
            [],
        )

    def test_reject_emits_no_ledger_record(self):
        r=review_candidate(
            candidate(),decision="REJECT",reviewer="authorized-reviewer",
            reviewed_at=REVIEWED,trusted_now=NOW
        )
        self.assertEqual(r["proposal_status"],"REJECTED")
        self.assertIsNone(r["ledger_record_proposal"])

    def test_future_review_rejected(self):
        with self.assertRaises(ValueError):
            review_candidate(
                candidate(),decision="APPROVE",reviewer="authorized-reviewer",
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
                candidate(),decision="AUTO",reviewer="authorized-reviewer",
                reviewed_at=REVIEWED,trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
