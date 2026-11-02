import io
import json
import unittest
import zipfile

from weatherapi_probe_receipt import build_receipt
from provider_github_artifact_metadata import build_trusted_binding
from provider_github_artifact_ingest import ingest_github_artifact

RUN=123456
COMMIT="a"*40
NOW="2026-11-02T21:00:00+00:00"

def metadata():
    return {
        "id":99,
        "name":"weatherapi-probe-receipt-123456",
        "size_in_bytes":2048,
        "expired":False,
        "created_at":"2026-11-02T20:50:00Z",
        "expires_at":"2026-11-09T20:50:00Z",
        "digest":"sha256:"+"b"*64,
        "workflow_run":{
            "id":RUN,
            "repository_id":123,
            "head_repository_id":123,
            "head_branch":"main",
            "head_sha":COMMIT,
        },
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

class ProviderGithubArtifactMetadataTests(unittest.TestCase):
    def test_valid_metadata_builds_binding(self):
        b=build_trusted_binding(metadata(),provider="WeatherAPI",trusted_now=NOW)
        self.assertEqual(b["expected_run_id"],str(RUN))
        self.assertEqual(b["expected_commit"],COMMIT)
        self.assertEqual(b["metadata_binding_status"],"GITHUB_ARTIFACT_METADATA_MATCH")

    def test_preferred_ingestion_uses_metadata_binding(self):
        r=ingest_github_artifact(
            metadata(),zip_receipt(),provider="WeatherAPI",trusted_now=NOW
        )
        self.assertEqual(r["status"],"REVIEW_ONLY")
        self.assertEqual(
            r["receipt_ingestion"]["candidate"]["reference"],
            "github-actions-run:"+str(RUN),
        )
        self.assertIs(
            r["receipt_ingestion"]["candidate"]["github_metadata_match"],True
        )
        self.assertFalse(r["ledger_mutation_permitted"])

    def test_artifact_name_must_match_run(self):
        m=metadata(); m["name"]="weatherapi-probe-receipt-999"
        with self.assertRaises(ValueError):
            build_trusted_binding(m,provider="WeatherAPI",trusted_now=NOW)

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

    def test_metadata_commit_mismatch_rejects_receipt(self):
        m=metadata(); m["workflow_run"]["head_sha"]="c"*40
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                m,zip_receipt(),provider="WeatherAPI",trusted_now=NOW
            )

    def test_metadata_run_mismatch_rejects_receipt(self):
        m=metadata()
        m["workflow_run"]["id"]=999
        m["name"]="weatherapi-probe-receipt-999"
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                m,zip_receipt(),provider="WeatherAPI",trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
