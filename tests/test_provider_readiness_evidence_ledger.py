import copy
import json
import unittest

from provider_readiness_evidence_gate import (
    evidence_supports_readiness,
    validate_ledger,
    validate_record,
)

def readiness():
    with open("config/provider_readiness.json", encoding="utf-8") as handle:
        return json.load(handle)

def ledger():
    with open("config/provider_evidence.json", encoding="utf-8") as handle:
        return json.load(handle)

def manual_record():
    return {
        "status":"VERIFIED",
        "source_type":"manual_review",
        "reference":"review:example",
        "reviewed_at":"2026-11-02T20:00:00+00:00",
        "reviewer":"authorized-reviewer",
    }

def github_record():
    return {
        "status":"VERIFIED",
        "source_type":"github_actions_receipt",
        "reference":"github-actions-run:123",
        "reviewed_at":"2026-11-02T20:00:00+00:00",
        "reviewer":"authorized-reviewer",
        "source_commit":"a"*40,
        "artifact_sha256":"b"*64,
    }

class ProviderReadinessEvidenceGateTests(unittest.TestCase):
    def test_committed_empty_ledger_is_valid_and_supports_false_readiness(self):
        l=ledger()
        self.assertEqual(validate_ledger(l),[])
        self.assertEqual(evidence_supports_readiness(readiness(),l),[])

    def test_true_provider_claim_requires_evidence(self):
        r=readiness()
        for entry in r["providers"]:
            if entry["name"]=="API-Sports":
                entry["live_auth_verified"]=True
        errors=evidence_supports_readiness(r,ledger())
        self.assertTrue(any("API-Sports live_auth_verified lacks evidence" in e for e in errors))

    def test_true_model_gate_requires_evidence(self):
        r=readiness()
        r["model_gates"]["historical_calibration_verified"]=True
        errors=evidence_supports_readiness(r,ledger())
        self.assertTrue(any("historical_calibration_verified lacks evidence" in e for e in errors))

    def test_matching_manual_evidence_supports_claim(self):
        r=readiness()
        l=ledger()
        for entry in r["providers"]:
            if entry["name"]=="SportsDataIO":
                entry["entitlement_verified"]=True
        for entry in l["providers"]:
            if entry["name"]=="SportsDataIO":
                entry["evidence"]["entitlement_verified"]=manual_record()
        self.assertEqual(evidence_supports_readiness(r,l),[])

    def test_github_receipt_requires_commit_and_hash(self):
        record=github_record()
        del record["artifact_sha256"]
        self.assertTrue(validate_record(record))
        record=github_record()
        del record["source_commit"]
        self.assertTrue(validate_record(record))

    def test_bad_commit_and_hash_rejected(self):
        record=github_record()
        record["source_commit"]="xyz"
        record["artifact_sha256"]="123"
        self.assertTrue(validate_record(record))

    def test_timestamp_must_be_timezone_aware(self):
        record=manual_record()
        record["reviewed_at"]="2026-11-02T20:00:00"
        self.assertTrue(validate_record(record))

    def test_extra_evidence_field_rejected(self):
        record=manual_record()
        record["raw_secret"]="forbidden"
        self.assertTrue(validate_record(record))

    def test_duplicate_provider_evidence_rejected(self):
        l=ledger()
        l["providers"].append(copy.deepcopy(l["providers"][0]))
        self.assertTrue(validate_ledger(l))

    def test_claim_coverage_must_be_exact(self):
        l=ledger()
        del l["providers"][0]["evidence"]["freshness_verified"]
        self.assertTrue(validate_ledger(l))

if __name__=="__main__":
    unittest.main()
