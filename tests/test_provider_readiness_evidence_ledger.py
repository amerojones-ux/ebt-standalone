import copy
import json
import unittest

from provider_readiness_evidence_gate import (
    evidence_supports_readiness,
    validate_ledger,
    validate_record,
)
from provider_live_request_plan import request_plan_sha256

NOW="2026-11-02T20:30:00+00:00"
REPO="amerojones-ux/ebt-standalone"

def readiness():
    with open("config/provider_readiness.json", encoding="utf-8") as handle:
        return json.load(handle)

def ledger():
    with open("config/provider_evidence.json", encoding="utf-8") as handle:
        return json.load(handle)

def manual_record(subject="SportsDataIO",claim="entitlement_verified"):
    return {
        "status":"VERIFIED",
        "subject":subject,
        "claim":claim,
        "source_type":"manual_review",
        "reference":"review:example",
        "reviewed_at":"2026-11-02T20:00:00+00:00",
        "reviewer":"authorized-reviewer",
    }

def github_record(subject="API-Sports",claim="live_auth_verified"):
    signer={
        "API-Sports":".github/workflows/apisports-status-probe.yml",
        "WeatherAPI":".github/workflows/weatherapi-live-probe.yml",
        "The Odds API":".github/workflows/theoddsapi-live-probe.yml",
        "TheRundown":".github/workflows/therundown-live-probe.yml",
    }.get(subject,".github/workflows/unsupported.yml")
    return {
        "status":"VERIFIED",
        "subject":subject,
        "claim":claim,
        "source_type":"github_actions_receipt",
        "reference":"github-actions-run:123",
        "reviewed_at":"2026-11-02T20:00:00+00:00",
        "reviewer":"github:reviewer#123",
        "source_repository":REPO,
        "source_commit":"a"*40,
        "receipt_sha256":"b"*64,
        "artifact_sha256":"c"*64,
        "attestation_marker_sha256":"d"*64,
        "request_plan_sha256":request_plan_sha256(subject),
        "attestation_id":"attestation-123",
        "attestation_url":"https://github.com/"+REPO+"/attestations/attestation-123",
        "signer_workflow":signer,
        "execution_intent_verified":True,
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
        "review_repository":REPO,
        "review_workflow_run_id":"777",
        "review_source_commit":"e"*40,
        "review_github_metadata_match":True,
        "review_decision_sha256":"f"*64,
        "review_decision_file_sha256":"1"*64,
        "review_attestation_marker_sha256":"2"*64,
        "review_attestation_id":"review-attestation-123",
        "review_attestation_url":"https://github.com/"+REPO+"/attestations/review-attestation-123",
        "review_signer_workflow":".github/workflows/provider-live-auth-evidence-review.yml",
    }

def report_record(subject="MODEL",claim="historical_calibration_verified"):
    return {
        "status":"VERIFIED",
        "subject":subject,
        "claim":claim,
        "source_type":"validation_report",
        "reference":"validation-report:calibration-v1",
        "reviewed_at":"2026-11-02T20:00:00+00:00",
        "reviewer":"authorized-reviewer",
        "artifact_sha256":"c"*64,
    }

class ProviderReadinessEvidenceGateTests(unittest.TestCase):
    def test_committed_empty_ledger_is_valid_and_supports_false_readiness(self):
        l=ledger()
        self.assertEqual(validate_ledger(l,trusted_now=NOW),[])
        self.assertEqual(evidence_supports_readiness(readiness(),l,trusted_now=NOW),[])

    def test_true_provider_claim_requires_evidence(self):
        r=readiness()
        for entry in r["providers"]:
            if entry["name"]=="API-Sports":
                entry["live_auth_verified"]=True
        errors=evidence_supports_readiness(r,ledger(),trusted_now=NOW)
        self.assertTrue(any("API-Sports live_auth_verified lacks evidence" in e for e in errors))

    def test_true_model_gate_requires_evidence(self):
        r=readiness()
        r["model_gates"]["historical_calibration_verified"]=True
        errors=evidence_supports_readiness(r,ledger(),trusted_now=NOW)
        self.assertTrue(any("historical_calibration_verified lacks evidence" in e for e in errors))

    def test_matching_manual_entitlement_evidence_supports_claim(self):
        r=readiness()
        l=ledger()
        for entry in r["providers"]:
            if entry["name"]=="SportsDataIO":
                entry["entitlement_verified"]=True
        for entry in l["providers"]:
            if entry["name"]=="SportsDataIO":
                entry["evidence"]["entitlement_verified"]=manual_record()
        self.assertEqual(evidence_supports_readiness(r,l,trusted_now=NOW),[])

    def test_matching_attested_live_auth_evidence_supports_claim(self):
        r=readiness()
        l=ledger()
        for entry in r["providers"]:
            if entry["name"]=="API-Sports":
                entry["live_auth_verified"]=True
        for entry in l["providers"]:
            if entry["name"]=="API-Sports":
                entry["evidence"]["live_auth_verified"]=github_record()
        self.assertEqual(evidence_supports_readiness(r,l,trusted_now=NOW),[])

    def test_matching_therundown_live_auth_evidence_is_valid_but_not_model_evidence(self):
        record=github_record(subject="TheRundown")
        self.assertEqual(
            validate_record(
                record,subject="TheRundown",
                claim="live_auth_verified",trusted_now=NOW
            ),
            [],
        )
        r=readiness()
        l=ledger()
        for entry in r["providers"]:
            if entry["name"]=="TheRundown":
                entry["live_auth_verified"]=True
                self.assertFalse(entry["model_evidence_allowed"])
        for entry in l["providers"]:
            if entry["name"]=="TheRundown":
                entry["evidence"]["live_auth_verified"]=record
                self.assertIsNone(entry["evidence"]["model_evidence_allowed"])
        self.assertEqual(evidence_supports_readiness(r,l,trusted_now=NOW),[])

    def test_live_auth_requires_github_actions_receipt(self):
        r=manual_record(subject="API-Sports",claim="live_auth_verified")
        errors=validate_record(r,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW)
        self.assertTrue(any("source_type not allowed" in e for e in errors))

    def test_identity_requires_validation_report(self):
        r=manual_record(subject="SportsDataIO",claim="identity_verified")
        errors=validate_record(r,subject="SportsDataIO",claim="identity_verified",trusted_now=NOW)
        self.assertTrue(any("source_type not allowed" in e for e in errors))

    def test_model_gate_requires_validation_report(self):
        r=manual_record(subject="MODEL",claim="historical_calibration_verified")
        errors=validate_record(r,subject="MODEL",claim="historical_calibration_verified",trusted_now=NOW)
        self.assertTrue(any("source_type not allowed" in e for e in errors))
        self.assertEqual(
            validate_record(report_record(),subject="MODEL",claim="historical_calibration_verified",trusted_now=NOW),
            [],
        )

    def test_github_receipt_requires_full_signed_provenance(self):
        fields=[
            "source_commit","receipt_sha256","artifact_sha256",
            "attestation_marker_sha256","request_plan_sha256",
            "attestation_id","attestation_url",
            "signer_workflow","source_repository",
            "execution_intent_verified","execution_intent_sha256",
            "execution_intent_file_sha256","execution_intent_marker_sha256",
            "execution_intent_bundle_sha256","execution_intent_attestation_id",
            "execution_intent_attestation_url","execution_actor",
            "execution_actor_id","execution_max_requests",
            "review_repository","review_workflow_run_id",
            "review_source_commit","review_github_metadata_match",
            "review_decision_sha256","review_decision_file_sha256",
            "review_attestation_marker_sha256","review_attestation_id",
            "review_attestation_url","review_signer_workflow",
        ]
        for field in fields:
            with self.subTest(field=field):
                record=github_record()
                del record[field]
                self.assertTrue(
                    validate_record(
                        record,subject="API-Sports",
                        claim="live_auth_verified",trusted_now=NOW
                    )
                )

    def test_execution_intent_authorization_fields_are_strict(self):
        for field in (
            "execution_intent_sha256",
            "execution_intent_file_sha256",
            "execution_intent_marker_sha256",
            "execution_intent_bundle_sha256",
        ):
            with self.subTest(field=field):
                record=github_record()
                record[field]="0"
                self.assertTrue(
                    validate_record(
                        record,subject="API-Sports",
                        claim="live_auth_verified",trusted_now=NOW
                    )
                )

        for bad in (True,0,2):
            with self.subTest(execution_max_requests=bad):
                record=github_record()
                record["execution_max_requests"]=bad
                self.assertTrue(
                    validate_record(
                        record,subject="API-Sports",
                        claim="live_auth_verified",trusted_now=NOW
                    )
                )

        record=github_record()
        record["execution_actor"]="bad actor"
        self.assertTrue(
            validate_record(
                record,subject="API-Sports",
                claim="live_auth_verified",trusted_now=NOW
            )
        )

    def test_free_form_reviewer_rejected_for_live_auth(self):
        record=github_record()
        record["reviewer"]="authorized-reviewer"
        self.assertTrue(
            validate_record(
                record,subject="API-Sports",
                claim="live_auth_verified",trusted_now=NOW
            )
        )

    def test_wrong_review_signer_or_repository_rejected(self):
        record=github_record()
        record["review_repository"]="other/repo"
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))
        record=github_record()
        record["review_signer_workflow"]=".github/workflows/other.yml"
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))

    def test_bad_review_hashes_and_run_id_rejected(self):
        record=github_record()
        record["review_workflow_run_id"]="x"
        record["review_decision_sha256"]="123"
        record["review_decision_file_sha256"]="123"
        record["review_attestation_marker_sha256"]="123"
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))

    def test_wrong_request_plan_fingerprint_rejected(self):
        record=github_record()
        record["request_plan_sha256"]="0"*64
        self.assertTrue(
            validate_record(
                record,subject="API-Sports",
                claim="live_auth_verified",trusted_now=NOW
            )
        )

    def test_bad_commit_and_hashes_rejected(self):
        record=github_record()
        record["source_commit"]="xyz"
        record["receipt_sha256"]="123"
        record["artifact_sha256"]="123"
        record["attestation_marker_sha256"]="123"
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))

    def test_wrong_repository_rejected(self):
        record=github_record()
        record["source_repository"]="other/repo"
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))

    def test_wrong_signer_workflow_rejected(self):
        record=github_record()
        record["signer_workflow"]=".github/workflows/weatherapi-live-probe.yml"
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))

    def test_wrong_attestation_url_rejected(self):
        record=github_record()
        record["attestation_url"]="https://example.com/attestation/123"
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))

    def test_subject_and_claim_mismatch_rejected(self):
        record=github_record()
        self.assertTrue(validate_record(record,subject="WeatherAPI",claim="live_auth_verified",trusted_now=NOW))
        self.assertTrue(validate_record(record,subject="API-Sports",claim="entitlement_verified",trusted_now=NOW))

    def test_future_review_rejected(self):
        record=github_record()
        record["reviewed_at"]="2026-11-02T21:00:00+00:00"
        errors=validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW)
        self.assertTrue(any("future" in e for e in errors))

    def test_timestamp_must_be_timezone_aware(self):
        record=manual_record()
        record["reviewed_at"]="2026-11-02T20:00:00"
        self.assertTrue(validate_record(record,subject="SportsDataIO",claim="entitlement_verified",trusted_now=NOW))

    def test_attestation_fields_for_manual_review_rejected(self):
        record=manual_record()
        record["attestation_id"]="not-allowed"
        self.assertTrue(validate_record(record,subject="SportsDataIO",claim="entitlement_verified",trusted_now=NOW))

    def test_extra_evidence_field_rejected(self):
        record=manual_record()
        record["raw_secret"]="forbidden"
        self.assertTrue(validate_record(record,subject="SportsDataIO",claim="entitlement_verified",trusted_now=NOW))

    def test_duplicate_provider_evidence_rejected(self):
        l=ledger()
        l["providers"].append(copy.deepcopy(l["providers"][0]))
        self.assertTrue(validate_ledger(l,trusted_now=NOW))

    def test_claim_coverage_must_be_exact(self):
        l=ledger()
        del l["providers"][0]["evidence"]["freshness_verified"]
        self.assertTrue(validate_ledger(l,trusted_now=NOW))

if __name__=="__main__":
    unittest.main()
