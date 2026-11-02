import hashlib
import io
import json
import unittest
import zipfile

from weatherapi_probe_receipt import build_receipt
from provider_github_artifact_metadata import (
    build_attestation_marker_binding,
    build_trusted_binding,
)
from provider_github_artifact_ingest import ingest_github_artifact

RUN=123456
COMMIT="a"*40
NOW="2026-11-02T21:00:00+00:00"
REPO="amerojones-ux/ebt-standalone"

def base_workflow():
    return {
        "id":RUN,
        "repository_id":123,
        "head_repository_id":123,
        "head_branch":"main",
        "head_sha":COMMIT,
    }

def metadata(zip_bytes=None):
    size=2048 if zip_bytes is None else len(zip_bytes)
    digest="b"*64 if zip_bytes is None else hashlib.sha256(zip_bytes).hexdigest()
    return {
        "id":99,
        "name":"weatherapi-probe-receipt-123456",
        "size_in_bytes":size,
        "expired":False,
        "created_at":"2026-11-02T20:50:00Z",
        "expires_at":"2026-11-09T20:50:00Z",
        "digest":"sha256:"+digest,
        "workflow_run":base_workflow(),
    }

def marker_metadata(zip_bytes=None):
    size=2048 if zip_bytes is None else len(zip_bytes)
    digest="c"*64 if zip_bytes is None else hashlib.sha256(zip_bytes).hexdigest()
    return {
        "id":100,
        "name":"weatherapi-attestation-verification-123456",
        "size_in_bytes":size,
        "expired":False,
        "created_at":"2026-11-02T20:52:00Z",
        "expires_at":"2026-11-09T20:52:00Z",
        "digest":"sha256:"+digest,
        "workflow_run":base_workflow(),
    }

def zip_receipt():
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_schema_fresh"},
        "2026-11-02T20:51:00+00:00",COMMIT,str(RUN)
    )
    raw=(json.dumps(receipt,sort_keys=True)+"\n").encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("weatherapi_probe_receipt.json",raw)
    return out.getvalue()

def verification_marker():
    body={
        "schema_version":2,
        "provider":"WeatherAPI",
        "verification_status":"VERIFIED",
        "repository":REPO,
        "workflow_run_id":str(RUN),
        "source_commit":COMMIT,
        "source_ref":"refs/heads/main",
        "signer_workflow":".github/workflows/weatherapi-live-probe.yml",
        "attestation_id":"attestation-123",
        "attestation_url":"https://github.com/"+REPO+"/attestations/attestation-123",
        "attestation_bundle_sha256":"f"*64,
        "receipt_file":"weatherapi_probe_receipt.json",
        "verification_tool":"gh attestation verify",
        "verification_modes":["local_bundle","github_api"],
    }
    canonical=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    marker=dict(body)
    marker["marker_sha256"]=hashlib.sha256(canonical).hexdigest()
    return marker

def zip_marker():
    raw=(json.dumps(verification_marker(),sort_keys=True)+"\n").encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("weatherapi_attestation_verification.json",raw)
    return out.getvalue()

class ProviderGithubArtifactMetadataTests(unittest.TestCase):
    def test_valid_receipt_metadata_builds_binding(self):
        b=build_trusted_binding(metadata(),provider="WeatherAPI",trusted_now=NOW)
        self.assertEqual(b["expected_run_id"],str(RUN))
        self.assertEqual(b["expected_commit"],COMMIT)
        self.assertEqual(b["artifact_kind"],"receipt")
        self.assertEqual(b["metadata_binding_status"],"GITHUB_ARTIFACT_METADATA_MATCH")

    def test_valid_marker_metadata_builds_binding(self):
        b=build_attestation_marker_binding(
            marker_metadata(),provider="WeatherAPI",trusted_now=NOW
        )
        self.assertEqual(b["expected_run_id"],str(RUN))
        self.assertEqual(b["artifact_kind"],"attestation_verification_marker")

    def test_preferred_ingestion_requires_receipt_and_verified_marker(self):
        receipt_zip=zip_receipt()
        marker_zip=zip_marker()
        r=ingest_github_artifact(
            metadata(receipt_zip),
            receipt_zip,
            marker_metadata(marker_zip),
            marker_zip,
            provider="WeatherAPI",
            repository=REPO,
            trusted_now=NOW,
        )
        self.assertEqual(r["status"],"REVIEW_ONLY")
        self.assertEqual(
            r["candidate"]["reference"],
            "github-actions-run:"+str(RUN),
        )
        self.assertIs(r["candidate"]["github_metadata_match"],True)
        self.assertIs(r["candidate"]["attestation_verified"],True)
        self.assertEqual(r["candidate"]["source_repository"],REPO)
        self.assertEqual(r["candidate"]["attestation_id"],"attestation-123")
        self.assertEqual(
            r["candidate"]["attestation_url"],
            "https://github.com/"+REPO+"/attestations/attestation-123",
        )
        self.assertEqual(
            r["candidate"]["signer_workflow"],
            ".github/workflows/weatherapi-live-probe.yml",
        )
        self.assertEqual(
            r["candidate"]["attestation_marker_sha256"],
            r["attestation_verification"]["marker_file_sha256"],
        )
        self.assertEqual(
            r["attestation_verification"]["attestation_bundle_sha256"],
            "f"*64,
        )
        self.assertEqual(
            r["attestation_verification"]["verification_modes"],
            ["local_bundle","github_api"],
        )
        self.assertFalse(r["ledger_mutation_permitted"])

    def test_receipt_zip_digest_mismatch_rejected(self):
        receipt_zip=zip_receipt()
        marker_zip=zip_marker()
        m=metadata(receipt_zip)
        m["digest"]="sha256:"+"0"*64
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                m,receipt_zip,marker_metadata(marker_zip),marker_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_receipt_zip_size_mismatch_rejected(self):
        receipt_zip=zip_receipt()
        marker_zip=zip_marker()
        m=metadata(receipt_zip)
        m["size_in_bytes"]+=1
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                m,receipt_zip,marker_metadata(marker_zip),marker_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_marker_zip_digest_mismatch_rejected(self):
        receipt_zip=zip_receipt()
        marker_zip=zip_marker()
        m=marker_metadata(marker_zip)
        m["digest"]="sha256:"+"0"*64
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                metadata(receipt_zip),receipt_zip,m,marker_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_artifact_name_must_match_run(self):
        m=metadata(); m["name"]="weatherapi-probe-receipt-999"
        with self.assertRaises(ValueError):
            build_trusted_binding(m,provider="WeatherAPI",trusted_now=NOW)

    def test_marker_artifact_name_must_match_run(self):
        m=marker_metadata(); m["name"]="weatherapi-attestation-verification-999"
        with self.assertRaises(ValueError):
            build_attestation_marker_binding(
                m,provider="WeatherAPI",trusted_now=NOW
            )

    def test_artifact_must_be_unexpired(self):
        m=metadata(); m["expired"]=True
        with self.assertRaises(ValueError):
            build_trusted_binding(m,provider="WeatherAPI",trusted_now=NOW)

    def test_expiration_time_must_be_future(self):
        m=metadata(); m["expires_at"]="2026-11-02T20:59:00Z"
        with self.assertRaises(ValueError):
            build_trusted_binding(m,provider="WeatherAPI",trusted_now=NOW)

    def test_branch_must_be_main(self):
        m=metadata(); m["workflow_run"]["head_branch"]="feature"
        with self.assertRaises(ValueError):
            build_trusted_binding(m,provider="WeatherAPI",trusted_now=NOW)

    def test_head_repository_must_match_repository(self):
        m=metadata(); m["workflow_run"]["head_repository_id"]=456
        with self.assertRaises(ValueError):
            build_trusted_binding(m,provider="WeatherAPI",trusted_now=NOW)

    def test_digest_must_be_sha256(self):
        m=metadata(); m["digest"]="md5:abc"
        with self.assertRaises(ValueError):
            build_trusted_binding(m,provider="WeatherAPI",trusted_now=NOW)

    def test_marker_run_mismatch_rejected(self):
        m=marker_metadata()
        m["workflow_run"]["id"]=999
        m["name"]="weatherapi-attestation-verification-999"
        with self.assertRaises(ValueError):
            receipt_zip=zip_receipt()
            marker_zip=zip_marker()
            ingest_github_artifact(
                metadata(receipt_zip),receipt_zip,m,marker_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_marker_commit_mismatch_rejected(self):
        receipt_zip=zip_receipt()
        marker_zip=zip_marker()
        m=marker_metadata(marker_zip)
        m["workflow_run"]["head_sha"]="c"*40
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                metadata(receipt_zip),receipt_zip,m,marker_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_marker_missing_dual_verification_modes_rejected(self):
        marker=verification_marker()
        marker["verification_modes"]=["github_api"]
        body={k:v for k,v in marker.items() if k!="marker_sha256"}
        marker["marker_sha256"]=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest()
        raw=json.dumps(marker).encode()
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w") as zf:
            zf.writestr("weatherapi_attestation_verification.json",raw)
        with self.assertRaises(ValueError):
            receipt_zip=zip_receipt()
            tampered_marker_zip=out.getvalue()
            ingest_github_artifact(
                metadata(receipt_zip),receipt_zip,
                marker_metadata(tampered_marker_zip),tampered_marker_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_marker_bad_bundle_hash_rejected(self):
        marker=verification_marker()
        marker["attestation_bundle_sha256"]="bad"
        body={k:v for k,v in marker.items() if k!="marker_sha256"}
        marker["marker_sha256"]=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest()
        raw=json.dumps(marker).encode()
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w") as zf:
            zf.writestr("weatherapi_attestation_verification.json",raw)
        with self.assertRaises(ValueError):
            receipt_zip=zip_receipt()
            tampered_marker_zip=out.getvalue()
            ingest_github_artifact(
                metadata(receipt_zip),receipt_zip,
                marker_metadata(tampered_marker_zip),tampered_marker_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_marker_content_tamper_rejected(self):
        marker=verification_marker()
        marker["source_commit"]="c"*40
        raw=json.dumps(marker).encode()
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w") as zf:
            zf.writestr("weatherapi_attestation_verification.json",raw)
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                metadata(),zip_receipt(),marker_metadata(),out.getvalue(),
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
