import copy
import unittest

from apisports_status_receipt import build_receipt
from provider_receipt_review_candidate import build_review_candidate, bind_attestation_verification
from provider_evidence_review_decision import review_candidate, verify_review_decision
from provider_evidence_ledger_preview import build_ledger_preview
import json

COMMIT="a"*40
RUN="12345"
ARTIFACT="d"*64
MARKER="e"*64
NOW="2026-11-02T21:00:00+00:00"
REVIEWED="2026-11-02T20:59:00+00:00"

def ledger():
    with open("config/provider_evidence.json",encoding="utf-8") as handle:
        return json.load(handle)

def decision():
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:58:00+00:00",COMMIT,RUN
    )
    pending=build_review_candidate(
        receipt,artifact_sha256=ARTIFACT,
        expected_run_id=RUN,expected_commit=COMMIT
    )
    candidate=bind_attestation_verification(pending,marker_sha256=MARKER)
    return review_candidate(
        candidate,decision="APPROVE",reviewer="authorized-reviewer",
        reviewed_at=REVIEWED,trusted_now=NOW
    )

class ProviderEvidenceLedgerPreviewTests(unittest.TestCase):
    def test_decision_checksum_verifies(self):
        self.assertTrue(verify_review_decision(decision()))

    def test_decision_mutation_fails(self):
        d=decision()
        d["reviewer"]="other"
        self.assertFalse(verify_review_decision(d))

    def test_approved_decision_builds_nonmutating_preview(self):
        original=ledger()
        result=build_ledger_preview(original,decision(),trusted_now=NOW)
        self.assertEqual(result["preview_status"],"VALID_MANUAL_PATCH_PREVIEW")
        self.assertFalse(result["ledger_write_permitted"])
        self.assertFalse(result["readiness_write_permitted"])
        self.assertFalse(result["forecast_activation_permitted"])
        self.assertIsNone(
            next(x for x in original["providers"] if x["name"]=="API-Sports")
            ["evidence"]["live_auth_verified"]
        )
        self.assertIsNotNone(
            next(x for x in result["preview_ledger"]["providers"] if x["name"]=="API-Sports")
            ["evidence"]["live_auth_verified"]
        )

    def test_rejected_decision_cannot_preview(self):
        receipt=build_receipt(
            {"status":"PASS","category":"authenticated_status_schema"},
            "2026-11-02T20:58:00+00:00",COMMIT,RUN
        )
        pending=build_review_candidate(
            receipt,artifact_sha256=ARTIFACT,
            expected_run_id=RUN,expected_commit=COMMIT
        )
        candidate=bind_attestation_verification(pending,marker_sha256=MARKER)
        rejected=review_candidate(
            candidate,decision="REJECT",reviewer="authorized-reviewer",
            reviewed_at=REVIEWED,trusted_now=NOW
        )
        with self.assertRaises(ValueError):
            build_ledger_preview(ledger(),rejected,trusted_now=NOW)

    def test_existing_evidence_cannot_be_overwritten(self):
        l=ledger()
        d=decision()
        for entry in l["providers"]:
            if entry["name"]=="API-Sports":
                entry["evidence"]["live_auth_verified"]=copy.deepcopy(
                    d["ledger_record_proposal"]
                )
        with self.assertRaises(ValueError):
            build_ledger_preview(l,d,trusted_now=NOW)

    def test_invalid_current_ledger_rejected(self):
        l=ledger()
        l["providers"].pop()
        with self.assertRaises(ValueError):
            build_ledger_preview(l,decision(),trusted_now=NOW)

if __name__=="__main__":
    unittest.main()
