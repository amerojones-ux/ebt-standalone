import hashlib
import json
import unittest

from provider_execution_intent import (
    CONTRACTS,
    build_execution_intent,
    verify_execution_intent,
)

REPO="amerojones-ux/ebt-standalone"
RUN="12345"
COMMIT="a"*40
NOW="2026-11-03T08:00:00+00:00"

def valid(provider):
    contract=CONTRACTS[provider]
    return build_execution_intent(
        provider=provider,
        repository=REPO,
        workflow_run_id=RUN,
        source_commit=COMMIT,
        source_ref="refs/heads/main",
        signer_workflow=contract["workflow"],
        actor="amerojones-ux",
        actor_id="262097315",
        generated_at_utc=NOW,
        review_authorization=contract["review_authorization"],
        request_authorization=contract["request_authorization"],
    )

def resign(value):
    body={k:v for k,v in value.items() if k!="intent_sha256"}
    value["intent_sha256"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return value

class ProviderExecutionIntentTests(unittest.TestCase):
    def test_all_supported_provider_intents_verify(self):
        for provider in CONTRACTS:
            with self.subTest(provider=provider):
                value=valid(provider)
                self.assertTrue(verify_execution_intent(value))
                self.assertEqual(value["max_requests"],1)
                self.assertFalse(value["ledger_mutation_permitted"])
                self.assertFalse(value["readiness_mutation_permitted"])
                self.assertFalse(value["forecast_activation_permitted"])
                self.assertEqual(len(value["request_plan_sha256"]),64)

    def test_wrong_review_authorization_rejected(self):
        value=valid("WeatherAPI")
        value["review_authorization"]="NO"
        resign(value)
        self.assertFalse(verify_execution_intent(value))

    def test_wrong_request_authorization_rejected(self):
        value=valid("The Odds API")
        value["request_authorization"]="NO"
        resign(value)
        self.assertFalse(verify_execution_intent(value))

    def test_wrong_repository_ref_or_workflow_rejected(self):
        for field,replacement in (
            ("repository","other/repo"),
            ("source_ref","refs/heads/feature"),
            ("signer_workflow",".github/workflows/other.yml"),
        ):
            with self.subTest(field=field):
                value=valid("API-Sports")
                value[field]=replacement
                resign(value)
                self.assertFalse(verify_execution_intent(value))

    def test_wrong_actor_identity_rejected(self):
        value=valid("WeatherAPI")
        value["actor"]="bad actor"
        resign(value)
        self.assertFalse(verify_execution_intent(value))
        value=valid("WeatherAPI")
        value["actor_id"]="abc"
        resign(value)
        self.assertFalse(verify_execution_intent(value))

    def test_request_plan_tamper_rejected(self):
        value=valid("API-Sports")
        value["request_plan_sha256"]="0"*64
        resign(value)
        self.assertFalse(verify_execution_intent(value))

    def test_request_count_cannot_be_bool_or_more_than_one(self):
        for bad in (True,2,0):
            with self.subTest(value=bad):
                value=valid("WeatherAPI")
                value["max_requests"]=bad
                resign(value)
                self.assertFalse(verify_execution_intent(value))

    def test_state_mutation_flags_cannot_be_enabled(self):
        for field in (
            "ledger_mutation_permitted",
            "readiness_mutation_permitted",
            "forecast_activation_permitted",
        ):
            with self.subTest(field=field):
                value=valid("The Odds API")
                value[field]=True
                resign(value)
                self.assertFalse(verify_execution_intent(value))

    def test_intent_checksum_tamper_rejected(self):
        value=valid("WeatherAPI")
        value["actor"]="other"
        self.assertFalse(verify_execution_intent(value))

if __name__=="__main__":
    unittest.main()
