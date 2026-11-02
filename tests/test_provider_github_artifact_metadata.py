import hashlib
import io
import json
import unittest
import zipfile

from weatherapi_probe_receipt import build_receipt
from provider_github_artifact_metadata import (
    build_attestation_bundle_binding,
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

def bundle_file():
    return (json.dumps(
        {"mediaType":"application/vnd.dev.sigstore.bundle+json;version=0.3","verificationMaterial":{}},
        sort_keys=True,
    )+"\n").encode()

def zip_one(name,payload):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name,payload)
    return out.getvalue()

def zip_receipt():
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_schema_fresh"},
        "2026-11-02T20:51:00+00:00",COMMIT,str(RUN)
    )
    raw=(json.dumps(receipt,sort_keys=True)+"\n").encode()
    return zip_one("weatherapi_probe_receipt.json",raw)

def verification_marker(bundle_bytes=None):
    bundle_bytes=bundle_file() if bundle_bytes is None else bundle_bytes
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
        "attestation_bundle_sha256":hashlib.sha256(bundle_bytes).hexdigest(),
        "receipt_file":"weatherapi_probe_receipt.json",
        "verification_tool":"gh attestation verify",
        "verification_modes":["local_bundle","github_api"],
    }
    canonical=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    marker=dict(body)
    marker["marker_sha256"]=hashlib.sha256(canonical).hexdigest()
    return marker

def zip_marker(bundle_bytes=None):
    raw=(json.dumps(verification_marker(bundle_bytes),sort_keys=True)+"\n").encode()
    return zip_one("weatherapi_attestation_verification.json",raw)

def zip_bundle(bundle_bytes=None):
    bundle_bytes=bundle_file() if bundle_bytes is None else bundle_bytes
    return zip_one("weatherapi_attestation_bundle.json",bundle_bytes)

def artifact_metadata(name,artifact_id,zip_bytes,created="2026-11-02T20:50:00Z"):
    return {
        "id":artifact_id,
        "name":name,
        "size_in_bytes":len(zip_bytes),
        "expired":False,
        "created_at":created,
        "expires_at":"2026-11-09T20:55:00Z",
        "digest":"sha256:"+hashlib.sha256(zip_bytes).hexdigest(),
        "workflow_run":base_workflow(),
    }

def metadata(zip_bytes):
    return artifact_metadata("weatherapi-probe-receipt-"+str(RUN),99,zip_bytes)

def marker_metadata(zip_bytes):
    return artifact_metadata(
        "weatherapi-attestation-verification-"+str(RUN),100,zip_bytes,
        "2026-11-02T20:52:00Z"
    )

def bundle_metadata(zip_bytes):
    return artifact_metadata(
        "weatherapi-attestation-bundle-"+str(RUN),101,zip_bytes,
        "2026-11-02T20:53:00Z"
    )

def good_inputs():
    receipt_zip=zip_receipt()
    bundle_zip=zip_bundle()
    marker_zip=zip_marker()
    return (
        metadata(receipt_zip),receipt_zip,
        marker_metadata(marker_zip),marker_zip,
        bundle_metadata(bundle_zip),bundle_zip,
    )

class ProviderGithubArtifactMetadataTests(unittest.TestCase):
    def test_valid_metadata_bindings(self):
        args=good_inputs()
        rb=build_trusted_binding(args[0],provider="WeatherAPI",trusted_now=NOW)
        mb=build_attestation_marker_binding(args[2],provider="WeatherAPI",trusted_now=NOW)
        bb=build_attestation_bundle_binding(args[4],provider="WeatherAPI",trusted_now=NOW)
        self.assertEqual(rb["artifact_kind"],"receipt")
        self.assertEqual(mb["artifact_kind"],"attestation_verification_marker")
        self.assertEqual(bb["artifact_kind"],"attestation_bundle")
        self.assertEqual(rb["expected_run_id"],str(RUN))
        self.assertEqual(bb["expected_commit"],COMMIT)

    def test_preferred_ingestion_requires_all_three_artifacts(self):
        args=good_inputs()
        r=ingest_github_artifact(
            *args,
            provider="WeatherAPI",repository=REPO,trusted_now=NOW
        )
        self.assertEqual(r["status"],"REVIEW_ONLY")
        self.assertIs(r["candidate"]["attestation_verified"],True)
        self.assertEqual(
            r["attestation_bundle"]["bundle_file_sha256"],
            r["attestation_verification"]["attestation_bundle_sha256"],
        )
        self.assertEqual(
            r["candidate"]["attestation_marker_sha256"],
            r["attestation_verification"]["marker_file_sha256"],
        )
        self.assertFalse(r["ledger_mutation_permitted"])

    def test_receipt_zip_digest_mismatch_rejected(self):
        args=list(good_inputs())
        args[0]["digest"]="sha256:"+"0"*64
        with self.assertRaises(ValueError):
            ingest_github_artifact(*args,provider="WeatherAPI",repository=REPO,trusted_now=NOW)

    def test_marker_zip_digest_mismatch_rejected(self):
        args=list(good_inputs())
        args[2]["digest"]="sha256:"+"0"*64
        with self.assertRaises(ValueError):
            ingest_github_artifact(*args,provider="WeatherAPI",repository=REPO,trusted_now=NOW)

    def test_bundle_zip_digest_mismatch_rejected(self):
        args=list(good_inputs())
        args[4]["digest"]="sha256:"+"0"*64
        with self.assertRaises(ValueError):
            ingest_github_artifact(*args,provider="WeatherAPI",repository=REPO,trusted_now=NOW)

    def test_bundle_file_hash_must_match_marker(self):
        args=list(good_inputs())
        tampered_bundle=(json.dumps({"tampered":True})+"\n").encode()
        tampered_zip=zip_bundle(tampered_bundle)
        args[4]=bundle_metadata(tampered_zip)
        args[5]=tampered_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(*args,provider="WeatherAPI",repository=REPO,trusted_now=NOW)

    def test_bundle_run_mismatch_rejected(self):
        args=list(good_inputs())
        args[4]["workflow_run"]["id"]=999
        args[4]["name"]="weatherapi-attestation-bundle-999"
        with self.assertRaises(ValueError):
            ingest_github_artifact(*args,provider="WeatherAPI",repository=REPO,trusted_now=NOW)

    def test_bundle_commit_mismatch_rejected(self):
        args=list(good_inputs())
        args[4]["workflow_run"]["head_sha"]="c"*40
        with self.assertRaises(ValueError):
            ingest_github_artifact(*args,provider="WeatherAPI",repository=REPO,trusted_now=NOW)

    def test_marker_missing_dual_verification_modes_rejected(self):
        receipt_zip=zip_receipt()
        bundle_zip=zip_bundle()
        marker=verification_marker()
        marker["verification_modes"]=["github_api"]
        body={k:v for k,v in marker.items() if k!="marker_sha256"}
        marker["marker_sha256"]=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest()
        marker_zip=zip_one(
            "weatherapi_attestation_verification.json",
            (json.dumps(marker,sort_keys=True)+"\n").encode(),
        )
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                metadata(receipt_zip),receipt_zip,
                marker_metadata(marker_zip),marker_zip,
                bundle_metadata(bundle_zip),bundle_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_marker_content_tamper_rejected(self):
        receipt_zip=zip_receipt()
        bundle_zip=zip_bundle()
        marker=verification_marker()
        marker["source_commit"]="c"*40
        marker_zip=zip_one(
            "weatherapi_attestation_verification.json",
            json.dumps(marker).encode(),
        )
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                metadata(receipt_zip),receipt_zip,
                marker_metadata(marker_zip),marker_zip,
                bundle_metadata(bundle_zip),bundle_zip,
                provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
