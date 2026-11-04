import copy
import hashlib
import json
import unittest

from provider_account_evidence import load_registry
from provider_account_metadata_claim import verify_account_metadata_claim
from provider_account_metadata_promotion_preview import (
    build_metadata_promotion_preview,
    verify_metadata_promotion_preview,
)
from provider_account_metadata_source_review import build_source_review_decision
from provider_account_metadata_transition import build_transition, load_configs

def claim_and_decision(provider="Sportradar"):
    if provider=="Sportradar":
        facts={
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        }
        ref="portal-snapshot-1"
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
        ref="support-case-12"
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
        ref="portal-snapshot-7"
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
    decision=build_source_review_decision(
        body,
        decision="APPROVE",
        reviewer="github:reviewer#123",
        source_reference=ref,
        reviewed_at="2026-11-04T03:30:00+00:00",
    )
    return body,decision

class ProviderAccountMetadataPromotionPreviewTests(unittest.TestCase):
    def test_valid_preview_rebuilds_current_state(self):
        claim,decision=claim_and_decision()
        preview=build_metadata_promotion_preview(claim,decision)
        self.assertTrue(verify_metadata_promotion_preview(preview))
        self.assertEqual(preview["provider"],"Sportradar")
        self.assertFalse(preview["metadata_write_permitted"])
        self.assertFalse(preview["network_request_permitted"])
        self.assertFalse(preview["forecast_activation_permitted"])
        self.assertFalse(preview["model_evidence_allowed"])

    def test_all_three_providers_can_build_preview(self):
        for provider in ("SportsDataIO","Sportradar","RapidAPI"):
            with self.subTest(provider=provider):
                claim,decision=claim_and_decision(provider)
                preview=build_metadata_promotion_preview(claim,decision)
                self.assertTrue(verify_metadata_promotion_preview(preview))
                self.assertEqual(preview["provider"],provider)

    def test_rejected_source_review_cannot_preview(self):
        claim,_=claim_and_decision()
        decision=build_source_review_decision(
            claim,
            decision="REJECT",
            reviewer="github:reviewer#123",
            source_reference=claim["source_reference"],
            reviewed_at="2026-11-04T03:30:00+00:00",
        )
        with self.assertRaisesRegex(ValueError,"must be APPROVE"):
            build_metadata_promotion_preview(claim,decision)

    def test_account_registry_drift_is_rejected(self):
        claim,decision=claim_and_decision()
        registry=copy.deepcopy(load_registry())
        target=next(p for p in registry["providers"] if p["name"]=="Sportradar")
        target["quota_verified"]=True
        with self.assertRaisesRegex(ValueError,"drifted"):
            build_metadata_promotion_preview(
                claim,decision,registry=registry,configs=load_configs()
            )

    def test_provider_config_drift_is_rejected(self):
        claim,decision=claim_and_decision("RapidAPI")
        configs=copy.deepcopy(load_configs())
        configs["RapidAPI"]["plan_name"]="Changed"
        with self.assertRaisesRegex(ValueError,"drifted"):
            build_metadata_promotion_preview(
                claim,decision,registry=load_registry(),configs=configs
            )

    def test_decision_binding_tamper_is_rejected(self):
        claim,decision=claim_and_decision()
        bad=dict(decision)
        bad["source_claim_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"source review decision invalid"):
            build_metadata_promotion_preview(claim,bad)

    def test_preview_checksum_and_safety_flags_bind(self):
        claim,decision=claim_and_decision()
        preview=build_metadata_promotion_preview(claim,decision)
        bad=dict(preview)
        bad["preview_sha256"]="0"*64
        self.assertFalse(verify_metadata_promotion_preview(bad))
        for key in (
            "metadata_write_permitted","network_request_permitted",
            "forecast_activation_permitted","model_evidence_allowed",
        ):
            with self.subTest(key=key):
                bad=dict(preview)
                bad[key]=True
                self.assertFalse(verify_metadata_promotion_preview(bad))

if __name__=="__main__":
    unittest.main()
