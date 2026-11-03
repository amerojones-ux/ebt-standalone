import hashlib
import json
import unittest

from provider_execution_intent import CONTRACTS
from provider_execution_intent_verification_marker import (
    SETUP_PYTHON_SHA,
    verify_execution_intent_marker,
)
from provider_live_request_plan import request_plan_sha256

REPO="amerojones-ux/ebt-standalone"
RUN="12345"
COMMIT="a"*40

def marker(provider="WeatherAPI"):
    contract=CONTRACTS[provider]
    body={
        "schema_version":1,
        "provider":provider,
        "verification_status":"VERIFIED",
        "repository":REPO,
        "workflow_run_id":RUN,
        "source_commit":COMMIT,
        "source_ref":"refs/heads/main",
        "signer_workflow":contract["workflow"],
        "actor":"amerojones-ux",
        "actor_id":"262097315",
        "intent_sha256":"1"*64,
        "intent_file_sha256":"2"*64,
        "request_plan_sha256":request_plan_sha256(provider),
        "max_requests":1,
        "attestation_id":"intent-attestation-1",
        "attestation_url":
            "https://github.com/"+REPO+"/attestations/intent-attestation-1",
        "attestation_bundle_sha256":"3"*64,
        "verification_tool":"gh attestation verify",
        "verification_modes":["local_bundle","github_api"],
        "runner_label":"ubuntu-24.04",
        "python_version":"3.13.7",
        "gh_version":"2.80.0",
        "setup_python_sha":SETUP_PYTHON_SHA,
    }
    canonical=json.dumps(
        body,sort_keys=True,separators=(",",":")
    ).encode()
    value=dict(body)
    value["marker_sha256"]=hashlib.sha256(canonical).hexdigest()
    return value

def resign(value):
    body={k:v for k,v in value.items() if k!="marker_sha256"}
    value["marker_sha256"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return value

class ProviderExecutionIntentVerificationMarkerTests(unittest.TestCase):
    def test_valid_markers_for_all_supported_providers(self):
        for provider in CONTRACTS:
            with self.subTest(provider=provider):
                self.assertTrue(
                    verify_execution_intent_marker(
                        marker(provider),
                        provider=provider,
                        expected_run_id=RUN,
                        expected_commit=COMMIT,
                    )
                )

    def test_wrong_run_or_commit_rejected(self):
        value=marker()
        self.assertFalse(
            verify_execution_intent_marker(
                value,provider="WeatherAPI",
                expected_run_id="999",expected_commit=COMMIT
            )
        )
        self.assertFalse(
            verify_execution_intent_marker(
                value,provider="WeatherAPI",
                expected_run_id=RUN,expected_commit="b"*40
            )
        )

    def test_request_plan_drift_rejected_even_when_resigned(self):
        value=marker()
        value["request_plan_sha256"]="0"*64
        resign(value)
        self.assertFalse(
            verify_execution_intent_marker(
                value,provider="WeatherAPI",
                expected_run_id=RUN,expected_commit=COMMIT
            )
        )

    def test_max_requests_bool_or_two_rejected(self):
        for bad in (True,2):
            with self.subTest(bad=bad):
                value=marker()
                value["max_requests"]=bad
                resign(value)
                self.assertFalse(
                    verify_execution_intent_marker(
                        value,provider="WeatherAPI",
                        expected_run_id=RUN,expected_commit=COMMIT
                    )
                )

    def test_actor_or_toolchain_drift_rejected(self):
        for field,bad in (
            ("actor","bad actor"),
            ("actor_id","abc"),
            ("runner_label","ubuntu-latest"),
            ("python_version","3.12.9"),
            ("setup_python_sha","0"*40),
        ):
            with self.subTest(field=field):
                value=marker()
                value[field]=bad
                resign(value)
                self.assertFalse(
                    verify_execution_intent_marker(
                        value,provider="WeatherAPI",
                        expected_run_id=RUN,expected_commit=COMMIT
                    )
                )

    def test_marker_checksum_tamper_rejected(self):
        value=marker()
        value["actor"]="other-user"
        self.assertFalse(
            verify_execution_intent_marker(
                value,provider="WeatherAPI",
                expected_run_id=RUN,expected_commit=COMMIT
            )
        )

if __name__=="__main__":
    unittest.main()
