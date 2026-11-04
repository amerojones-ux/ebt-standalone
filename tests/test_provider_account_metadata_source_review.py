import hashlib
import json
import unittest

from provider_account_metadata_transition import build_transition
from provider_account_metadata_claim import verify_account_metadata_claim
from provider_account_metadata_source_review import (
    build_source_review_decision,
    verify_source_review_decision,
)

def make_claim(provider="Sportradar",ref="portal-snapshot-1"):
    if provider=="Sportradar":
        facts={
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        }
    elif provider=="SportsDataIO":
        facts={
            "source_type":"PROVIDER_SUPPORT",
            "scope_status":"RECONCILED",
            "product_name":"NFL League API",
            "feed_scope":"Scores",
            "endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress",
            "quota_reviewed":True,
            "overage_reviewed":True,
        }
    else:
        facts={
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"Example Sports Provider",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREE",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://example-sports.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
        }
    transition=build_transition(provider,facts)
    assert transition["status"]=="VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW",transition
    body={
        "schema_version":2,
        "claim_type":"ACCOUNT_METADATA_CLAIM",
        "provider":provider,
        "source_type":facts["source_type"],
        "source_reference":ref,
        "submitted_facts":facts,
        "submitter":"github:amerojones-ux#262097315",
        "repository":"amerojones-ux/ebt-standalone",
        "workflow_run_id":"12345",
        "workflow_run_attempt":1,
        "source_commit":"a"*40,
        "transition":transition,
        "claim_verified_against_provider_source":False,
        "write_permitted":False,
        "network_request_permitted":False,
        "forecast_activation_permitted":False,
    }
    raw=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    body["claim_sha256"]=hashlib.sha256(raw).hexdigest()
    assert verify_account_metadata_claim(body)
    return body

class ProviderAccountMetadataSourceReviewTests(unittest.TestCase):
    def test_approve_marks_source_match_but_not_promotion(self):
        claim=make_claim()
        decision=build_source_review_decision(
            claim,
            decision="APPROVE",
            reviewer="github:reviewer#123",
            source_reference="portal-snapshot-1",
            reviewed_at="2026-11-04T03:20:00+00:00",
        )
        self.assertTrue(verify_source_review_decision(decision))
        self.assertTrue(decision["provider_source_reviewed"])
        self.assertTrue(decision["provider_source_match"])
        self.assertTrue(decision["claim_verified_against_provider_source"])
        self.assertIsNotNone(decision["approved_transition"])
        self.assertFalse(decision["metadata_promotion_permitted"])
        self.assertFalse(decision["network_request_permitted"])
        self.assertFalse(decision["forecast_activation_permitted"])
        self.assertFalse(decision["model_evidence_allowed"])

    def test_reject_has_no_approved_transition(self):
        claim=make_claim("RapidAPI","support-ticket-77")
        decision=build_source_review_decision(
            claim,
            decision="REJECT",
            reviewer="github:reviewer#123",
            source_reference="support-ticket-77",
            reviewed_at="2026-11-04T03:20:00+00:00",
        )
        self.assertTrue(verify_source_review_decision(decision))
        self.assertFalse(decision["provider_source_match"])
        self.assertFalse(decision["claim_verified_against_provider_source"])
        self.assertIsNone(decision["approved_transition"])

    def test_source_reference_must_match_signed_claim(self):
        claim=make_claim()
        with self.assertRaisesRegex(ValueError,"does not match"):
            build_source_review_decision(
                claim,
                decision="APPROVE",
                reviewer="github:reviewer#123",
                source_reference="different-reference",
            )

    def test_invalid_or_tampered_claim_is_rejected(self):
        claim=make_claim()
        claim["claim_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"claim invalid"):
            build_source_review_decision(
                claim,
                decision="APPROVE",
                reviewer="github:reviewer#123",
                source_reference="portal-snapshot-1",
            )

    def test_reviewer_identity_and_decision_are_strict(self):
        claim=make_claim()
        with self.assertRaisesRegex(ValueError,"reviewer invalid"):
            build_source_review_decision(
                claim,
                decision="APPROVE",
                reviewer="manual-reviewer",
                source_reference="portal-snapshot-1",
            )
        with self.assertRaisesRegex(ValueError,"decision must"):
            build_source_review_decision(
                claim,
                decision="HOLD",
                reviewer="github:reviewer#123",
                source_reference="portal-snapshot-1",
            )

    def test_tampered_review_flags_fail_verification(self):
        claim=make_claim("SportsDataIO","support-case-12")
        decision=build_source_review_decision(
            claim,
            decision="APPROVE",
            reviewer="github:reviewer#123",
            source_reference="support-case-12",
            reviewed_at="2026-11-04T03:20:00+00:00",
        )
        for key in (
            "metadata_promotion_permitted",
            "network_request_permitted",
            "forecast_activation_permitted",
            "model_evidence_allowed",
        ):
            with self.subTest(key=key):
                bad=dict(decision)
                bad[key]=True
                self.assertFalse(verify_source_review_decision(bad))
        bad=dict(decision)
        bad["provider_source_match"]=False
        self.assertFalse(verify_source_review_decision(bad))

    def test_checksum_is_binding(self):
        claim=make_claim()
        decision=build_source_review_decision(
            claim,
            decision="APPROVE",
            reviewer="github:reviewer#123",
            source_reference="portal-snapshot-1",
            reviewed_at="2026-11-04T03:20:00+00:00",
        )
        bad=dict(decision)
        bad["decision_sha256"]="f"*64
        self.assertFalse(verify_source_review_decision(bad))

if __name__=="__main__":
    unittest.main()
