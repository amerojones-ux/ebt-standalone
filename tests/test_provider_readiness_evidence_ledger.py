import copy
import json
import unittest

from provider_readiness_evidence_gate import (
    evidence_supports_readiness,
    validate_ledger,
    validate_record,
)

NOW="2026-11-02T20:30:00+00:00"

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
    return {
        "status":"VERIFIED",
        "subject":subject,
        "claim":claim,
        "source_type":"github_actions_receipt",
        "reference":"github-actions-run:123",
        "reviewed_at":"2026-11-02T20:00:00+00:00",
        "reviewer":"authorized-reviewer",
        "source_commit":"a"*40,
        "artifact_sha256":"b"*64,
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

    def test_github_receipt_requires_commit_and_hash(self):
        record=github_record()
        del record["artifact_sha256"]
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))
        record=github_record()
        del record["source_commit"]
        self.assertTrue(validate_record(record,subject="API-Sports",claim="live_auth_verified",trusted_now=NOW))

    def test_bad_commit_and_hash_rejected(self):
        record=github_record()
        record["source_commit"]="xyz"
        record["artifact_sha256"]="123"
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
