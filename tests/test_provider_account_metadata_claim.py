import hashlib
import json
import unittest

from provider_account_metadata_claim import verify_account_metadata_claim
from provider_account_metadata_transition import build_transition

def make_claim(provider,facts):
    transition=build_transition(provider,facts)
    assert transition["status"]=="VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW",transition
    body={
        "schema_version":2,
        "claim_type":"ACCOUNT_METADATA_CLAIM",
        "provider":provider,
        "source_type":facts["source_type"],
        "source_reference":"support-ticket-123",
        "submitted_facts":facts,
        "submitter":"github:amerojones-ux#262097315",
        "repository":"amerojones-ux/ebt-standalone",
        "workflow_run_id":"123456",
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
    return body

class ProviderAccountMetadataClaimTests(unittest.TestCase):
    def test_valid_sportradar_claim_verifies(self):
        claim=make_claim("Sportradar",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        })
        self.assertTrue(verify_account_metadata_claim(claim))

    def test_valid_rapidapi_claim_verifies(self):
        claim=make_claim("RapidAPI",{
            "source_type":"PROVIDER_SUPPORT",
            "product_name":"Example Sports Provider",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREEMIUM",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://example-sports.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        self.assertTrue(verify_account_metadata_claim(claim))

    def test_claim_cannot_assert_provider_source_verification(self):
        claim=make_claim("Sportradar",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"production",
            "quota_reviewed":True,
        })
        claim["claim_verified_against_provider_source"]=True
        self.assertFalse(verify_account_metadata_claim(claim))

    def test_mutating_or_network_flags_invalidate_claim(self):
        claim=make_claim("Sportradar",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        })
        for key in ("write_permitted","network_request_permitted","forecast_activation_permitted"):
            with self.subTest(key=key):
                bad=dict(claim)
                bad[key]=True
                self.assertFalse(verify_account_metadata_claim(bad))

    def test_transition_unsafe_flags_invalidate_claim(self):
        claim=make_claim("RapidAPI",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"Example Sports Provider",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREE",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://example-sports.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        for key in ("network_request_permitted","model_evidence_allowed"):
            with self.subTest(key=key):
                bad=json.loads(json.dumps(claim))
                bad["transition"][key]=True
                self.assertFalse(verify_account_metadata_claim(bad))

    def test_checksum_and_exact_fields_are_required(self):
        claim=make_claim("Sportradar",{
            "source_type":"PROVIDER_SUPPORT",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        })
        bad=dict(claim)
        bad["claim_sha256"]="0"*64
        self.assertFalse(verify_account_metadata_claim(bad))
        bad=dict(claim)
        bad["unexpected"]="x"
        self.assertFalse(verify_account_metadata_claim(bad))
        bad={k:v for k,v in claim.items() if k!="source_reference"}
        self.assertFalse(verify_account_metadata_claim(bad))

if __name__=="__main__":
    unittest.main()
