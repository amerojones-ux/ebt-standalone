import hashlib
import json
import unittest

from provider_promotion_preview_attestation_marker import (
    PROMOTION_WORKFLOW,
    SOURCE_REPOSITORY,
    verify_promotion_preview_attestation_marker,
)

RUN="555"
REVIEW_RUN="444"
SOURCE_RUN="333"
COMMIT="a"*40

def marker():
    body={
        "schema_version":2,
        "verification_status":"VERIFIED",
        "repository":SOURCE_REPOSITORY,
        "promotion_workflow_run_id":RUN,
        "promotion_workflow_run_attempt":1,
        "review_workflow_run_id":REVIEW_RUN,
        "source_probe_run_id":SOURCE_RUN,
        "source_commit":COMMIT,
        "source_ref":"refs/heads/main",
        "signer_workflow":PROMOTION_WORKFLOW,
        "preview_file":"provider_live_auth_promotion_preview.json",
        "preview_sha256":"1"*64,
        "preview_file_sha256":"2"*64,
        "global_provider_gate":"SAFE_HOLD",
        "attestation_id":"preview-attestation-1",
        "attestation_url":
            "https://github.com/"+SOURCE_REPOSITORY+"/attestations/preview-attestation-1",
        "verification_tool":"gh attestation verify",
    }
    value=dict(body)
    value["marker_sha256"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return value

def resign(value):
    body={k:v for k,v in value.items() if k!="marker_sha256"}
    value["marker_sha256"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return value

class PromotionPreviewAttestationMarkerTests(unittest.TestCase):
    def verify(self,value):
        return verify_promotion_preview_attestation_marker(
            value,
            expected_run_id=RUN,
            expected_commit=COMMIT,
            expected_review_run_id=REVIEW_RUN,
            expected_source_probe_run_id=SOURCE_RUN,
        )

    def test_valid_marker_verifies(self):
        self.assertTrue(self.verify(marker()))

    def test_attempt_must_be_integer_one(self):
        for bad in (True,0,2,"1"):
            with self.subTest(bad=bad):
                value=marker()
                value["promotion_workflow_run_attempt"]=bad
                resign(value)
                self.assertFalse(self.verify(value))

    def test_run_commit_and_upstream_run_bindings_are_strict(self):
        cases=(
            ("promotion_workflow_run_id","999"),
            ("review_workflow_run_id","999"),
            ("source_probe_run_id","999"),
            ("source_commit","b"*40),
        )
        for field,bad in cases:
            with self.subTest(field=field):
                value=marker()
                value[field]=bad
                resign(value)
                self.assertFalse(self.verify(value))

    def test_safe_hold_signer_and_file_contract_are_strict(self):
        cases=(
            ("global_provider_gate","APPROVED"),
            ("signer_workflow",".github/workflows/other.yml"),
            ("preview_file","other.json"),
            ("source_ref","refs/heads/feature"),
        )
        for field,bad in cases:
            with self.subTest(field=field):
                value=marker()
                value[field]=bad
                resign(value)
                self.assertFalse(self.verify(value))

    def test_hash_url_and_attestation_contract_are_strict(self):
        cases=(
            ("preview_sha256","x"),
            ("preview_file_sha256","x"),
            ("attestation_id","bad id"),
            ("attestation_url","https://example.com/a"),
            ("verification_tool","other"),
        )
        for field,bad in cases:
            with self.subTest(field=field):
                value=marker()
                value[field]=bad
                resign(value)
                self.assertFalse(self.verify(value))

    def test_checksum_tamper_rejected(self):
        value=marker()
        value["global_provider_gate"]="APPROVED"
        self.assertFalse(self.verify(value))

if __name__=="__main__":
    unittest.main()
