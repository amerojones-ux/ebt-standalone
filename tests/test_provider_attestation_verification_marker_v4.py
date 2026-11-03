import hashlib
import json
import unittest

from provider_attestation_verification_marker import (
    REQUIRED_ATTESTATION_FLAGS,
    SETUP_PYTHON_SHA,
    verify_marker,
)
from provider_live_request_plan import request_plan_sha256

REPO="amerojones-ux/ebt-standalone"
RUN="12345"
COMMIT="a"*40

def marker(plan_sha=None,schema_version=4):
    body={
        "schema_version":schema_version,
        "provider":"WeatherAPI",
        "verification_status":"VERIFIED",
        "repository":REPO,
        "workflow_run_id":RUN,
        "source_commit":COMMIT,
        "source_ref":"refs/heads/main",
        "signer_workflow":".github/workflows/weatherapi-live-probe.yml",
        "attestation_id":"attestation-123",
        "attestation_url":"https://github.com/"+REPO+"/attestations/attestation-123",
        "attestation_bundle_sha256":"b"*64,
        "receipt_file":"weatherapi_probe_receipt.json",
        "verification_tool":"gh attestation verify",
        "verification_modes":["local_bundle","github_api"],
        "runner_label":"ubuntu-24.04",
        "python_version":"3.13.7",
        "gh_version":"2.80.0",
        "setup_python_sha":SETUP_PYTHON_SHA,
        "request_plan_sha256":(
            request_plan_sha256("WeatherAPI")
            if plan_sha is None else plan_sha
        ),
        "required_attestation_flags":list(REQUIRED_ATTESTATION_FLAGS),
    }
    canonical=json.dumps(
        body,sort_keys=True,separators=(",",":")
    ).encode("utf-8")
    result=dict(body)
    result["marker_sha256"]=hashlib.sha256(canonical).hexdigest()
    return result

class ProviderAttestationVerificationMarkerV4Tests(unittest.TestCase):
    def test_valid_v4_marker_verifies(self):
        self.assertTrue(
            verify_marker(
                marker(),
                provider="WeatherAPI",
                repository=REPO,
                expected_run_id=RUN,
                expected_commit=COMMIT,
            )
        )

    def test_schema_v3_marker_rejected(self):
        self.assertFalse(
            verify_marker(
                marker(schema_version=3),
                provider="WeatherAPI",
                repository=REPO,
                expected_run_id=RUN,
                expected_commit=COMMIT,
            )
        )

    def test_wrong_request_plan_fingerprint_rejected_even_with_valid_marker_checksum(self):
        value=marker(plan_sha="0"*64)
        self.assertFalse(
            verify_marker(
                value,
                provider="WeatherAPI",
                repository=REPO,
                expected_run_id=RUN,
                expected_commit=COMMIT,
            )
        )

    def test_provider_plan_cross_binding_rejected(self):
        value=marker(plan_sha=request_plan_sha256("The Odds API"))
        self.assertFalse(
            verify_marker(
                value,
                provider="WeatherAPI",
                repository=REPO,
                expected_run_id=RUN,
                expected_commit=COMMIT,
            )
        )

    def test_marker_checksum_tamper_rejected(self):
        value=marker()
        value["request_plan_sha256"]="f"*64
        self.assertFalse(
            verify_marker(
                value,
                provider="WeatherAPI",
                repository=REPO,
                expected_run_id=RUN,
                expected_commit=COMMIT,
            )
        )

if __name__=="__main__":
    unittest.main()
