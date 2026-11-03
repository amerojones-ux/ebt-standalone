import hashlib
import io
import json
import unittest
from unittest.mock import patch
import zipfile

from provider_promotion_preview_package_ingest import (
    ingest_promotion_preview_package,
)

REPO="amerojones-ux/ebt-standalone"
RUN=41719559583
REVIEW=41719029128
COMMIT="a"*40
NOW="2026-11-03T21:12:30+00:00"

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def decision():
    return {
        "decision":"APPROVE",
        "subject":"WeatherAPI",
        "claim":"live_auth_verified",
        "review_workflow_run_id":str(REVIEW),
        "decision_sha256":"1"*64,
    }

def preview():
    body={
        "preview_status":"VALID_LIVE_AUTH_PROMOTION_PREVIEW",
        "provider":"WeatherAPI",
        "claim":"live_auth_verified",
        "decision_sha256":"1"*64,
        "global_provider_gate":"SAFE_HOLD",
        "ledger_write_permitted":False,
        "readiness_write_permitted":False,
        "forecast_activation_permitted":False,
        "preview_ledger":{"schema_version":5},
        "preview_readiness":{"forecast_enabled":False},
    }
    value=dict(body)
    value["preview_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return value

def marker(preview_bytes,preview_value):
    return {
        "promotion_workflow_run_id":str(RUN),
        "promotion_workflow_run_attempt":1,
        "review_workflow_run_id":str(REVIEW),
        "source_probe_run_id":"41717111914",
        "preview_sha256":preview_value["preview_sha256"],
        "preview_file_sha256":hashlib.sha256(preview_bytes).hexdigest(),
    }

def metadata(run_attempt=1):
    return {
        "id":123,
        "name":f"provider-live-auth-promotion-preview-{REVIEW}-{RUN}",
        "size_in_bytes":1000,
        "expired":False,
        "created_at":"2026-11-03T21:12:02Z",
        "expires_at":"2026-11-10T21:12:02Z",
        "digest":"sha256:"+"b"*64,
        "workflow_run":{
            "id":RUN,
            "run_attempt":run_attempt,
            "repository_id":1166399648,
            "head_repository_id":1166399648,
            "head_branch":"main",
            "head_sha":COMMIT,
        },
    }

def package_bytes(*,extra=False,tamper_preview=False,tamper_marker_file_sha=False):
    pv=preview()
    if tamper_preview:
        pv["provider"]="API-Sports"
    pv_bytes=(json.dumps(pv,sort_keys=True)+"\n").encode()
    mk=marker(pv_bytes,pv)
    if tamper_marker_file_sha:
        mk["preview_file_sha256"]="0"*64
    files={
        "provider_attested_review_decision.json":
            (json.dumps(decision(),sort_keys=True)+"\n").encode(),
        "provider_live_auth_promotion_preview.json":pv_bytes,
        "provider_live_auth_promotion_preview_attestation_verification.json":
            (json.dumps(mk,sort_keys=True)+"\n").encode(),
    }
    if extra:
        files["extra.txt"]=b"x"
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_STORED) as zf:
        for name,data in files.items():
            zf.writestr(name,data)
    return out.getvalue()

class PromotionPreviewPackageIngestTests(unittest.TestCase):
    @patch("provider_promotion_preview_package_ingest.verify_promotion_preview_attestation_marker",return_value=True)
    @patch("provider_promotion_preview_package_ingest.verify_attested_review_decision",return_value=True)
    def test_valid_package_ingests(self,_decision,_marker):
        data=package_bytes()
        meta=metadata()
        meta["size_in_bytes"]=len(data)
        result=ingest_promotion_preview_package(meta,data,repository=REPO,trusted_now=NOW)
        self.assertEqual(result["package_status"],"VERIFIED_LIVE_AUTH_PROMOTION_PREVIEW_PACKAGE")
        self.assertEqual(result["provider"],"WeatherAPI")
        self.assertEqual(result["promotion_preview_run_id"],str(RUN))
        self.assertEqual(result["review_run_id"],str(REVIEW))

    @patch("provider_promotion_preview_package_ingest.verify_promotion_preview_attestation_marker",return_value=True)
    @patch("provider_promotion_preview_package_ingest.verify_attested_review_decision",return_value=True)
    def test_attempt_must_be_one(self,_decision,_marker):
        data=package_bytes()
        meta=metadata(run_attempt=2)
        meta["size_in_bytes"]=len(data)
        with self.assertRaises(ValueError):
            ingest_promotion_preview_package(meta,data,repository=REPO,trusted_now=NOW)

    @patch("provider_promotion_preview_package_ingest.verify_promotion_preview_attestation_marker",return_value=True)
    @patch("provider_promotion_preview_package_ingest.verify_attested_review_decision",return_value=True)
    def test_exact_file_set_required(self,_decision,_marker):
        data=package_bytes(extra=True)
        meta=metadata()
        meta["size_in_bytes"]=len(data)
        with self.assertRaises(ValueError):
            ingest_promotion_preview_package(meta,data,repository=REPO,trusted_now=NOW)

    @patch("provider_promotion_preview_package_ingest.verify_promotion_preview_attestation_marker",return_value=True)
    @patch("provider_promotion_preview_package_ingest.verify_attested_review_decision",return_value=True)
    def test_preview_checksum_tamper_rejected(self,_decision,_marker):
        data=package_bytes(tamper_preview=True)
        meta=metadata()
        meta["size_in_bytes"]=len(data)
        with self.assertRaises(ValueError):
            ingest_promotion_preview_package(meta,data,repository=REPO,trusted_now=NOW)

    @patch("provider_promotion_preview_package_ingest.verify_promotion_preview_attestation_marker",return_value=True)
    @patch("provider_promotion_preview_package_ingest.verify_attested_review_decision",return_value=True)
    def test_preview_file_binding_tamper_rejected(self,_decision,_marker):
        data=package_bytes(tamper_marker_file_sha=True)
        meta=metadata()
        meta["size_in_bytes"]=len(data)
        with self.assertRaises(ValueError):
            ingest_promotion_preview_package(meta,data,repository=REPO,trusted_now=NOW)

if __name__=="__main__":
    unittest.main()
