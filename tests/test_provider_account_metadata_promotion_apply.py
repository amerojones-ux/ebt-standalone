import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from provider_account_evidence import load_registry
from provider_account_metadata_claim import verify_account_metadata_claim
from provider_account_metadata_promotion_apply import (
    PROVIDER_CONFIG_PATHS,
    build_metadata_promotion_apply,
    verify_metadata_promotion_apply,
)
from provider_account_metadata_promotion_preview import (
    BODY_FIELDS as PREVIEW_BODY_FIELDS,
    build_metadata_promotion_preview,
)
from provider_account_metadata_source_review import build_source_review_decision
from provider_account_metadata_transition import build_transition, load_configs

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode()

def claim_decision_preview(provider="Sportradar"):
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
    body["claim_sha256"]=hashlib.sha256(canonical(body)).hexdigest()
    assert verify_account_metadata_claim(body)
    decision=build_source_review_decision(
        body,
        decision="APPROVE",
        reviewer="github:reviewer#123",
        source_reference=ref,
        reviewed_at="2026-11-04T03:30:00+00:00",
    )
    preview=build_metadata_promotion_preview(
        body,
        decision,
        source_review_run_id="777",
        source_review_commit="b"*40,
    )
    return body,decision,preview

def build_apply(claim,decision,preview,**kwargs):
    return build_metadata_promotion_apply(
        claim,
        decision,
        preview,
        promotion_preview_run_id="888",
        promotion_preview_commit="c"*40,
        **kwargs,
    )

def resign_preview(preview):
    body={k:preview[k] for k in PREVIEW_BODY_FIELDS}
    preview["preview_sha256"]=hashlib.sha256(canonical(body)).hexdigest()
    return preview

class ProviderAccountMetadataPromotionApplyTests(unittest.TestCase):
    def test_all_three_providers_build_valid_branch_only_apply(self):
        for provider in ("SportsDataIO","Sportradar","RapidAPI"):
            with self.subTest(provider=provider):
                claim,decision,preview=claim_decision_preview(provider)
                manifest=build_apply(claim,decision,preview)
                self.assertTrue(verify_metadata_promotion_apply(manifest))
                self.assertEqual(manifest["provider"],provider)
                self.assertEqual(
                    manifest["target_provider_config_path"],
                    PROVIDER_CONFIG_PATHS[provider],
                )
                self.assertEqual(
                    manifest["target_account_evidence_path"],
                    "config/provider_account_evidence.json",
                )
                self.assertTrue(manifest["isolated_branch_write_permitted"])
                self.assertFalse(manifest["main_write_permitted"])
                self.assertFalse(manifest["provider_network_request_permitted"])
                self.assertFalse(manifest["forecast_activation_permitted"])
                self.assertFalse(manifest["model_evidence_allowed"])

    def test_exact_file_byte_hashes_are_bound(self):
        claim,decision,preview=claim_decision_preview("RapidAPI")
        manifest=build_apply(claim,decision,preview)
        registry_bytes=(json.dumps(
            manifest["candidate_registry"],indent=2,sort_keys=True
        )+"\n").encode()
        provider_bytes=(json.dumps(
            manifest["candidate_provider_config"],indent=2,sort_keys=True
        )+"\n").encode()
        self.assertEqual(
            manifest["account_evidence_file_sha256"],
            hashlib.sha256(registry_bytes).hexdigest(),
        )
        self.assertEqual(
            manifest["provider_config_file_sha256"],
            hashlib.sha256(provider_bytes).hexdigest(),
        )

    def test_stale_preview_current_state_drift_is_rejected(self):
        claim,decision,preview=claim_decision_preview()
        configs=copy.deepcopy(load_configs())
        configs["Sportradar"]["product_name"]="drifted"
        with self.assertRaisesRegex(ValueError,"drifted"):
            build_apply(
                claim,decision,preview,
                registry=load_registry(),configs=configs,
            )

    def test_already_applied_promotion_is_rejected_as_noop(self):
        claim,decision,preview=claim_decision_preview("SportsDataIO")
        registry=copy.deepcopy(preview["candidate_registry"])
        configs=copy.deepcopy(preview["candidate_configs"])
        with self.assertRaisesRegex(ValueError,"no-op|already applied|drifted"):
            build_apply(
                claim,decision,preview,
                registry=registry,configs=configs,
            )

    def test_forged_cross_provider_config_mutation_is_rejected(self):
        claim,decision,preview=claim_decision_preview("Sportradar")
        forged=copy.deepcopy(preview)
        forged["candidate_configs"]["RapidAPI"]["plan_name"]="forbidden-cross-provider"
        forged=resign_preview(forged)
        with patch(
            "provider_account_metadata_promotion_apply.build_metadata_promotion_preview",
            return_value=forged,
        ):
            with self.assertRaisesRegex(ValueError,"cross-provider config mutation|candidate account/config consistency invalid"):
                build_apply(claim,decision,forged)

    def test_forged_cross_provider_registry_mutation_is_rejected(self):
        claim,decision,preview=claim_decision_preview("Sportradar")
        forged=copy.deepcopy(preview)
        rapid=next(
            p for p in forged["candidate_registry"]["providers"]
            if p["name"]=="RapidAPI"
        )
        rapid["quota_verified"]=True
        forged=resign_preview(forged)
        with patch(
            "provider_account_metadata_promotion_apply.build_metadata_promotion_preview",
            return_value=forged,
        ):
            with self.assertRaisesRegex(ValueError,"cross-provider account evidence"):
                build_apply(claim,decision,forged)

    def test_candidate_safety_flags_are_independently_enforced(self):
        claim,decision,preview=claim_decision_preview("RapidAPI")
        forged=copy.deepcopy(preview)
        target=next(
            p for p in forged["candidate_registry"]["providers"]
            if p["name"]=="RapidAPI"
        )
        target["live_request_permitted"]=True
        forged=resign_preview(forged)
        with patch(
            "provider_account_metadata_promotion_apply.build_metadata_promotion_preview",
            return_value=forged,
        ):
            with self.assertRaises(ValueError):
                build_apply(claim,decision,forged)

    def test_manifest_checksum_and_permissions_are_binding(self):
        claim,decision,preview=claim_decision_preview()
        manifest=build_apply(claim,decision,preview)
        bad=dict(manifest)
        bad["apply_sha256"]="0"*64
        self.assertFalse(verify_metadata_promotion_apply(bad))
        for key,value in (
            ("isolated_branch_write_permitted",False),
            ("main_write_permitted",True),
            ("provider_network_request_permitted",True),
            ("forecast_activation_permitted",True),
            ("model_evidence_allowed",True),
        ):
            with self.subTest(key=key):
                bad=dict(manifest)
                bad[key]=value
                self.assertFalse(verify_metadata_promotion_apply(bad))

if __name__=="__main__":
    unittest.main()
