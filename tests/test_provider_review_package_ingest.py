import hashlib
import io
import json
import unittest
import zipfile

from apisports_status_receipt import build_receipt
from provider_attested_review_decision import verify_attested_review_decision
from provider_evidence_review_decision import review_candidate
from provider_receipt_review_candidate import (
    bind_attestation_verification,
    build_review_candidate,
)
from provider_review_package_ingest import ingest_review_package

SOURCE_RUN="12345"
REVIEW_RUN=777
COMMIT="a"*40
REVIEW_COMMIT="f"*40
ARTIFACT="d"*64
MARKER="e"*64
REPO="amerojones-ux/ebt-standalone"
PROVIDER_ATTESTATION_ID="attestation-123"
PROVIDER_ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+PROVIDER_ATTESTATION_ID
PROVIDER_SIGNER=".github/workflows/apisports-status-probe.yml"
REVIEWER="github:reviewer#123"
REVIEW_SIGNER=".github/workflows/provider-live-auth-evidence-review.yml"
REVIEW_ATTESTATION_ID="review-attestation-456"
REVIEW_ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+REVIEW_ATTESTATION_ID
REVIEWED="2026-11-02T20:59:00+00:00"
NOW="2026-11-02T21:00:00+00:00"

def candidate():
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:58:00+00:00",COMMIT,SOURCE_RUN
    )
    pending=build_review_candidate(
        receipt,
        artifact_sha256=ARTIFACT,
        expected_run_id=SOURCE_RUN,
        expected_commit=COMMIT,
    )
    return bind_attestation_verification(
        pending,
        marker_sha256=MARKER,
        source_repository=REPO,
        attestation_id=PROVIDER_ATTESTATION_ID,
        attestation_url=PROVIDER_ATTESTATION_URL,
        signer_workflow=PROVIDER_SIGNER,
    )

def decision(value="APPROVE"):
    return review_candidate(
        candidate(),
        decision=value,
        reviewer=REVIEWER,
        reviewed_at=REVIEWED,
        trusted_now=NOW,
    )

def review_marker(reviewer=REVIEWER,commit=REVIEW_COMMIT):
    body={
        "schema_version":1,
        "verification_status":"VERIFIED",
        "repository":REPO,
        "review_workflow_run_id":str(REVIEW_RUN),
        "source_commit":commit,
        "source_ref":"refs/heads/main",
        "signer_workflow":REVIEW_SIGNER,
        "reviewer":reviewer,
        "attestation_id":REVIEW_ATTESTATION_ID,
        "attestation_url":REVIEW_ATTESTATION_URL,
        "decision_file":"provider_review_decision.json",
        "verification_tool":"gh attestation verify",
    }
    canonical=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    marker=dict(body)
    marker["marker_sha256"]=hashlib.sha256(canonical).hexdigest()
    return marker

def metadata(name=None,run_id=REVIEW_RUN,commit=REVIEW_COMMIT):
    return {
        "id":500,
        "name":name or f"provider-live-auth-review-{SOURCE_RUN}-{run_id}",
        "size_in_bytes":4096,
        "expired":False,
        "created_at":"2026-11-02T20:59:10Z",
        "expires_at":"2026-11-09T20:59:10Z",
        "digest":"sha256:"+"9"*64,
        "workflow_run":{
            "id":run_id,
            "repository_id":123,
            "head_repository_id":123,
            "head_branch":"main",
            "head_sha":commit,
        },
    }

def package_zip(decision_value="APPROVE",marker=None,extra=None,decision_obj=None):
    files={
        "provider_review_candidate.json":candidate(),
        "provider_review_decision.json":decision_obj or decision(decision_value),
        "provider_review_decision_attestation_verification.json":marker or review_marker(),
    }
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        for name,value in files.items():
            zf.writestr(name,(json.dumps(value,sort_keys=True)+"\n").encode())
        if extra is not None:
            zf.writestr(extra,b"x")
    return out.getvalue()

class ProviderReviewPackageIngestTests(unittest.TestCase):
    def test_valid_approved_package_becomes_attested_decision(self):
        result=ingest_review_package(
            metadata(),package_zip(),repository=REPO,trusted_now=NOW
        )
        self.assertTrue(verify_attested_review_decision(result))
        self.assertEqual(
            result["attested_status"],
            "ATTESTED_APPROVED_FOR_MANUAL_LEDGER_REVIEW",
        )
        self.assertEqual(result["reviewer"],REVIEWER)
        proposal=result["ledger_record_proposal"]
        self.assertEqual(proposal["review_repository"],REPO)
        self.assertEqual(proposal["review_workflow_run_id"],str(REVIEW_RUN))
        self.assertEqual(proposal["review_source_commit"],REVIEW_COMMIT)
        self.assertEqual(proposal["review_signer_workflow"],REVIEW_SIGNER)
        self.assertTrue(proposal["review_github_metadata_match"])

    def test_valid_rejected_package_is_attested_without_proposal(self):
        result=ingest_review_package(
            metadata(),package_zip("REJECT"),repository=REPO,trusted_now=NOW
        )
        self.assertTrue(verify_attested_review_decision(result))
        self.assertEqual(result["attested_status"],"ATTESTED_REJECTED")
        self.assertIsNone(result["ledger_record_proposal"])

    def test_wrong_repository_rejected(self):
        with self.assertRaises(ValueError):
            ingest_review_package(
                metadata(),package_zip(),repository="other/repo",trusted_now=NOW
            )

    def test_extra_file_rejected(self):
        with self.assertRaises(ValueError):
            ingest_review_package(
                metadata(),package_zip(extra="extra.txt"),
                repository=REPO,trusted_now=NOW
            )

    def test_source_run_name_mismatch_rejected(self):
        bad=metadata(name=f"provider-live-auth-review-999-{REVIEW_RUN}")
        with self.assertRaises(ValueError):
            ingest_review_package(
                bad,package_zip(),repository=REPO,trusted_now=NOW
            )

    def test_review_run_name_mismatch_rejected(self):
        bad=metadata(name=f"provider-live-auth-review-{SOURCE_RUN}-999")
        with self.assertRaises(ValueError):
            ingest_review_package(
                bad,package_zip(),repository=REPO,trusted_now=NOW
            )

    def test_review_commit_marker_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            ingest_review_package(
                metadata(),
                package_zip(marker=review_marker(commit="c"*40)),
                repository=REPO,trusted_now=NOW,
            )

    def test_reviewer_marker_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            ingest_review_package(
                metadata(),
                package_zip(marker=review_marker(reviewer="github:other#999")),
                repository=REPO,trusted_now=NOW,
            )

    def test_marker_checksum_tamper_rejected(self):
        marker=review_marker()
        marker["reviewer"]="github:other#999"
        with self.assertRaises(ValueError):
            ingest_review_package(
                metadata(),package_zip(marker=marker),
                repository=REPO,trusted_now=NOW
            )

    def test_decision_checksum_tamper_rejected(self):
        bad=decision()
        bad["reviewer"]="github:other#999"
        with self.assertRaises(ValueError):
            ingest_review_package(
                metadata(),package_zip(decision_obj=bad),
                repository=REPO,trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
