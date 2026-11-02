import copy
import json
import unittest

from apisports_status_receipt import build_receipt
from provider_attested_review_decision import (
    sign_attested_review_decision,
    verify_attested_review_decision,
)
from provider_evidence_review_decision import review_candidate
from provider_evidence_ledger_preview import build_ledger_preview
from provider_receipt_review_candidate import (
    bind_attestation_verification,
    build_review_candidate,
)

COMMIT="a"*40
RUN="12345"
ARTIFACT="d"*64
MARKER="e"*64
REPO="amerojones-ux/ebt-standalone"
ATTESTATION_ID="attestation-123"
ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+ATTESTATION_ID
SIGNER=".github/workflows/apisports-status-probe.yml"
REVIEWER="github:reviewer#123"
REVIEW_RUN="777"
REVIEW_COMMIT="f"*40
REVIEW_DECISION_FILE_SHA="1"*64
REVIEW_MARKER_FILE_SHA="2"*64
REVIEW_ATTESTATION_ID="review-attestation-123"
REVIEW_ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+REVIEW_ATTESTATION_ID
REVIEW_SIGNER=".github/workflows/provider-live-auth-evidence-review.yml"
NOW="2026-11-02T21:00:00+00:00"
REVIEWED="2026-11-02T20:59:00+00:00"

def ledger():
    with open("config/provider_evidence.json",encoding="utf-8") as handle:
        return json.load(handle)

def raw_decision(decision="APPROVE"):
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:58:00+00:00",COMMIT,RUN
    )
    pending=build_review_candidate(
        receipt,artifact_sha256=ARTIFACT,
        expected_run_id=RUN,expected_commit=COMMIT
    )
    candidate=bind_attestation_verification(
        pending,
        marker_sha256=MARKER,
        source_repository=REPO,
        attestation_id=ATTESTATION_ID,
        attestation_url=ATTESTATION_URL,
        signer_workflow=SIGNER,
    )
    return review_candidate(
        candidate,decision=decision,reviewer=REVIEWER,
        reviewed_at=REVIEWED,trusted_now=NOW
    )

def attested_decision(decision="APPROVE"):
    raw=raw_decision(decision)
    proposal=copy.deepcopy(raw["ledger_record_proposal"])
    if decision=="APPROVE":
        proposal.update({
            "review_repository":REPO,
            "review_workflow_run_id":REVIEW_RUN,
            "review_source_commit":REVIEW_COMMIT,
            "review_github_metadata_match":True,
            "review_decision_sha256":raw["decision_sha256"],
            "review_decision_file_sha256":REVIEW_DECISION_FILE_SHA,
            "review_attestation_marker_sha256":REVIEW_MARKER_FILE_SHA,
            "review_attestation_id":REVIEW_ATTESTATION_ID,
            "review_attestation_url":REVIEW_ATTESTATION_URL,
            "review_signer_workflow":REVIEW_SIGNER,
        })
        status="ATTESTED_APPROVED_FOR_MANUAL_LEDGER_REVIEW"
    else:
        status="ATTESTED_REJECTED"

    return sign_attested_review_decision({
        "subject":raw["subject"],
        "claim":raw["claim"],
        "decision":raw["decision"],
        "reviewer":raw["reviewer"],
        "reviewed_at":raw["reviewed_at"],
        "candidate_sha256":raw["candidate_sha256"],
        "decision_sha256":raw["decision_sha256"],
        "attested_status":status,
        "review_repository":REPO,
        "review_workflow_run_id":REVIEW_RUN,
        "review_source_commit":REVIEW_COMMIT,
        "review_github_metadata_match":True,
        "review_decision_file_sha256":REVIEW_DECISION_FILE_SHA,
        "review_attestation_marker_sha256":REVIEW_MARKER_FILE_SHA,
        "review_attestation_id":REVIEW_ATTESTATION_ID,
        "review_attestation_url":REVIEW_ATTESTATION_URL,
        "review_signer_workflow":REVIEW_SIGNER,
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
        "ledger_record_proposal":proposal,
    })

class ProviderEvidenceLedgerPreviewTests(unittest.TestCase):
    def test_attested_decision_checksum_verifies(self):
        self.assertTrue(verify_attested_review_decision(attested_decision()))

    def test_attested_decision_mutation_fails(self):
        d=attested_decision()
        d["reviewer"]="github:other#999"
        self.assertFalse(verify_attested_review_decision(d))

    def test_raw_decision_cannot_preview(self):
        with self.assertRaises(ValueError):
            build_ledger_preview(ledger(),raw_decision(),trusted_now=NOW)

    def test_approved_attested_decision_builds_nonmutating_preview(self):
        original=ledger()
        result=build_ledger_preview(
            original,attested_decision(),trusted_now=NOW
        )
        self.assertEqual(result["preview_status"],"VALID_MANUAL_PATCH_PREVIEW")
        self.assertEqual(len(result["attested_decision_sha256"]),64)
        self.assertFalse(result["ledger_write_permitted"])
        self.assertFalse(result["readiness_write_permitted"])
        self.assertFalse(result["forecast_activation_permitted"])
        self.assertIsNone(
            next(x for x in original["providers"] if x["name"]=="API-Sports")
            ["evidence"]["live_auth_verified"]
        )
        record=next(
            x for x in result["preview_ledger"]["providers"]
            if x["name"]=="API-Sports"
        )["evidence"]["live_auth_verified"]
        self.assertEqual(record["review_repository"],REPO)
        self.assertEqual(record["review_workflow_run_id"],REVIEW_RUN)
        self.assertEqual(record["review_signer_workflow"],REVIEW_SIGNER)

    def test_attested_rejection_cannot_preview(self):
        with self.assertRaises(ValueError):
            build_ledger_preview(
                ledger(),attested_decision("REJECT"),trusted_now=NOW
            )

    def test_existing_evidence_cannot_be_overwritten(self):
        l=ledger()
        d=attested_decision()
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
            build_ledger_preview(l,attested_decision(),trusted_now=NOW)

if __name__=="__main__":
    unittest.main()
