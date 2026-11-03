import hashlib
import io
import json
import unittest
import zipfile

from weatherapi_probe_receipt import build_receipt
from provider_execution_intent import build_execution_intent
from provider_github_artifact_metadata import (
    build_attestation_bundle_binding,
    build_attestation_marker_binding,
    build_execution_intent_binding,
    build_execution_intent_bundle_binding,
    build_execution_intent_marker_binding,
    build_trusted_binding,
)
from provider_github_artifact_ingest import ingest_github_artifact
from provider_live_request_plan import request_plan_sha256

RUN=123456
COMMIT="a"*40
NOW="2026-11-02T21:00:00+00:00"
REPO="amerojones-ux/ebt-standalone"
ACTOR="amerojones-ux"
ACTOR_ID="262097315"
SETUP_PYTHON_SHA="6d4fd22b20465ccc0f7354476588e8df7c9ca0e0"

def base_workflow():
    return {
        "id":RUN,
        "repository_id":123,
        "head_repository_id":123,
        "head_branch":"main",
        "head_sha":COMMIT,
    }

def receipt_bundle_file():
    return (
        json.dumps(
            {
                "mediaType":
                "application/vnd.dev.sigstore.bundle+json;version=0.3",
                "verificationMaterial":{"kind":"receipt"},
            },
            sort_keys=True,
        )+"\n"
    ).encode()

def intent_bundle_file():
    return (
        json.dumps(
            {
                "mediaType":
                "application/vnd.dev.sigstore.bundle+json;version=0.3",
                "verificationMaterial":{"kind":"execution-intent"},
            },
            sort_keys=True,
        )+"\n"
    ).encode()

def zip_one(name,payload):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name,payload)
    return out.getvalue()

def zip_receipt(intent_sha=None):
    intent_sha=(
        execution_intent()["intent_sha256"]
        if intent_sha is None else intent_sha
    )
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_schema_fresh"},
        "2026-11-02T20:51:00+00:00",COMMIT,str(RUN),
        intent_sha,
    )
    raw=(json.dumps(receipt,sort_keys=True)+"\n").encode()
    return zip_one("weatherapi_probe_receipt.json",raw)

def receipt_verification_marker(bundle_bytes=None):
    bundle_bytes=(
        receipt_bundle_file() if bundle_bytes is None else bundle_bytes
    )
    body={
        "schema_version":4,
        "provider":"WeatherAPI",
        "verification_status":"VERIFIED",
        "repository":REPO,
        "workflow_run_id":str(RUN),
        "source_commit":COMMIT,
        "source_ref":"refs/heads/main",
        "signer_workflow":".github/workflows/weatherapi-live-probe.yml",
        "attestation_id":"receipt-attestation-123",
        "attestation_url":
            "https://github.com/"+REPO+"/attestations/receipt-attestation-123",
        "attestation_bundle_sha256":hashlib.sha256(bundle_bytes).hexdigest(),
        "receipt_file":"weatherapi_probe_receipt.json",
        "verification_tool":"gh attestation verify",
        "verification_modes":["local_bundle","github_api"],
        "runner_label":"ubuntu-24.04",
        "python_version":"3.13.7",
        "gh_version":"2.80.0",
        "setup_python_sha":SETUP_PYTHON_SHA,
        "request_plan_sha256":request_plan_sha256("WeatherAPI"),
        "required_attestation_flags":[
            "--bundle","--repo","--signer-workflow",
            "--source-ref","--source-digest","--format",
        ],
    }
    canonical=json.dumps(
        body,sort_keys=True,separators=(",",":")
    ).encode()
    marker=dict(body)
    marker["marker_sha256"]=hashlib.sha256(canonical).hexdigest()
    return marker

def zip_marker(bundle_bytes=None):
    raw=(
        json.dumps(
            receipt_verification_marker(bundle_bytes),sort_keys=True
        )+"\n"
    ).encode()
    return zip_one("weatherapi_attestation_verification.json",raw)

def zip_bundle(bundle_bytes=None):
    payload=receipt_bundle_file() if bundle_bytes is None else bundle_bytes
    return zip_one("weatherapi_attestation_bundle.json",payload)

def execution_intent(max_requests_override=None):
    value=build_execution_intent(
        provider="WeatherAPI",
        repository=REPO,
        workflow_run_id=str(RUN),
        source_commit=COMMIT,
        source_ref="refs/heads/main",
        signer_workflow=".github/workflows/weatherapi-live-probe.yml",
        actor=ACTOR,
        actor_id=ACTOR_ID,
        generated_at_utc="2026-11-02T20:49:00+00:00",
        review_authorization=
            "I_CONFIRM_WEATHERAPI_PLAN_QUOTA_AND_BILLING_REVIEWED",
        request_authorization="I_APPROVE_ONE_WEATHERAPI_REQUEST",
    )
    if max_requests_override is not None:
        value["max_requests"]=max_requests_override
        body={k:v for k,v in value.items() if k!="intent_sha256"}
        value["intent_sha256"]=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest()
    return value

def execution_intent_raw(value=None):
    value=execution_intent() if value is None else value
    return (json.dumps(value,sort_keys=True)+"\n").encode()

def zip_intent(value=None):
    return zip_one(
        "provider_execution_intent.json",
        execution_intent_raw(value),
    )

def intent_verification_marker(
    *,
    intent_value=None,
    intent_bundle_bytes=None,
    actor=ACTOR,
    request_plan=None,
):
    intent_value=execution_intent() if intent_value is None else intent_value
    intent_raw=execution_intent_raw(intent_value)
    intent_bundle_bytes=(
        intent_bundle_file()
        if intent_bundle_bytes is None
        else intent_bundle_bytes
    )
    body={
        "schema_version":1,
        "provider":"WeatherAPI",
        "verification_status":"VERIFIED",
        "repository":REPO,
        "workflow_run_id":str(RUN),
        "source_commit":COMMIT,
        "source_ref":"refs/heads/main",
        "signer_workflow":".github/workflows/weatherapi-live-probe.yml",
        "actor":actor,
        "actor_id":ACTOR_ID,
        "intent_sha256":intent_value["intent_sha256"],
        "intent_file_sha256":hashlib.sha256(intent_raw).hexdigest(),
        "request_plan_sha256":(
            request_plan_sha256("WeatherAPI")
            if request_plan is None else request_plan
        ),
        "max_requests":intent_value["max_requests"],
        "attestation_id":"intent-attestation-456",
        "attestation_url":
            "https://github.com/"+REPO+"/attestations/intent-attestation-456",
        "attestation_bundle_sha256":
            hashlib.sha256(intent_bundle_bytes).hexdigest(),
        "verification_tool":"gh attestation verify",
        "verification_modes":["local_bundle","github_api"],
        "runner_label":"ubuntu-24.04",
        "python_version":"3.13.7",
        "gh_version":"2.80.0",
        "setup_python_sha":SETUP_PYTHON_SHA,
    }
    canonical=json.dumps(
        body,sort_keys=True,separators=(",",":")
    ).encode()
    marker=dict(body)
    marker["marker_sha256"]=hashlib.sha256(canonical).hexdigest()
    return marker

def zip_intent_marker(**kwargs):
    marker=intent_verification_marker(**kwargs)
    raw=(json.dumps(marker,sort_keys=True)+"\n").encode()
    return zip_one(
        "weatherapi_execution_intent_attestation_verification.json",
        raw,
    )

def zip_intent_bundle(bundle_bytes=None):
    payload=intent_bundle_file() if bundle_bytes is None else bundle_bytes
    return zip_one(
        "weatherapi_execution_intent_attestation_bundle.json",
        payload,
    )

def artifact_metadata(
    name,artifact_id,zip_bytes,created="2026-11-02T20:50:00Z"
):
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
    return artifact_metadata(
        "weatherapi-probe-receipt-"+str(RUN),99,zip_bytes
    )

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

def intent_metadata(zip_bytes):
    return artifact_metadata(
        "weatherapi-execution-intent-"+str(RUN),102,zip_bytes,
        "2026-11-02T20:49:00Z"
    )

def intent_marker_metadata(zip_bytes):
    return artifact_metadata(
        "weatherapi-execution-intent-attestation-verification-"+str(RUN),
        103,zip_bytes,"2026-11-02T20:50:00Z"
    )

def intent_bundle_metadata(zip_bytes):
    return artifact_metadata(
        "weatherapi-execution-intent-attestation-bundle-"+str(RUN),
        104,zip_bytes,"2026-11-02T20:50:30Z"
    )

def good_inputs():
    receipt_zip=zip_receipt()
    marker_zip=zip_marker()
    bundle_zip=zip_bundle()
    intent_zip=zip_intent()
    intent_marker_zip=zip_intent_marker()
    intent_bundle_zip=zip_intent_bundle()
    return (
        metadata(receipt_zip),receipt_zip,
        marker_metadata(marker_zip),marker_zip,
        bundle_metadata(bundle_zip),bundle_zip,
        intent_metadata(intent_zip),intent_zip,
        intent_marker_metadata(intent_marker_zip),intent_marker_zip,
        intent_bundle_metadata(intent_bundle_zip),intent_bundle_zip,
    )

class ProviderGithubArtifactMetadataTests(unittest.TestCase):
    def test_valid_metadata_bindings_cover_full_authorized_chain(self):
        args=good_inputs()
        rb=build_trusted_binding(
            args[0],provider="WeatherAPI",trusted_now=NOW
        )
        mb=build_attestation_marker_binding(
            args[2],provider="WeatherAPI",trusted_now=NOW
        )
        bb=build_attestation_bundle_binding(
            args[4],provider="WeatherAPI",trusted_now=NOW
        )
        ib=build_execution_intent_binding(
            args[6],provider="WeatherAPI",trusted_now=NOW
        )
        imb=build_execution_intent_marker_binding(
            args[8],provider="WeatherAPI",trusted_now=NOW
        )
        ibb=build_execution_intent_bundle_binding(
            args[10],provider="WeatherAPI",trusted_now=NOW
        )
        self.assertEqual(rb["artifact_kind"],"receipt")
        self.assertEqual(mb["artifact_kind"],"attestation_verification_marker")
        self.assertEqual(bb["artifact_kind"],"attestation_bundle")
        self.assertEqual(ib["artifact_kind"],"execution_intent")
        self.assertEqual(
            imb["artifact_kind"],"execution_intent_verification_marker"
        )
        self.assertEqual(
            ibb["artifact_kind"],"execution_intent_attestation_bundle"
        )
        for binding in (mb,bb,ib,imb,ibb):
            self.assertEqual(binding["expected_run_id"],rb["expected_run_id"])
            self.assertEqual(binding["expected_commit"],rb["expected_commit"])

    def test_preferred_ingestion_requires_full_authorized_evidence_chain(self):
        args=good_inputs()
        result=ingest_github_artifact(
            *args,
            provider="WeatherAPI",repository=REPO,trusted_now=NOW
        )
        self.assertEqual(result["status"],"REVIEW_ONLY")
        self.assertIs(result["candidate"]["attestation_verified"],True)
        self.assertEqual(
            result["attestation_bundle"]["bundle_file_sha256"],
            result["attestation_verification"]["attestation_bundle_sha256"],
        )
        self.assertEqual(
            result["execution_intent_bundle"]["bundle_file_sha256"],
            result["execution_intent_verification"][
                "attestation_bundle_sha256"
            ],
        )
        self.assertEqual(
            result["execution_intent"]["intent_sha256"],
            result["execution_intent_verification"]["intent_sha256"],
        )
        self.assertEqual(
            result["receipt_execution_intent_sha256"],
            result["execution_intent"]["intent_sha256"],
        )
        self.assertEqual(
            result["execution_intent"]["actor"],
            result["execution_intent_verification"]["actor"],
        )
        self.assertEqual(result["execution_intent"]["max_requests"],1)
        self.assertIs(result["candidate"]["execution_intent_verified"],True)
        self.assertEqual(
            result["candidate"]["execution_intent_sha256"],
            result["execution_intent"]["intent_sha256"],
        )
        self.assertEqual(
            result["candidate"]["execution_intent_file_sha256"],
            result["execution_intent"]["intent_file_sha256"],
        )
        self.assertEqual(
            result["candidate"]["execution_intent_marker_sha256"],
            result["execution_intent_verification"]["marker_file_sha256"],
        )
        self.assertEqual(
            result["candidate"]["execution_intent_bundle_sha256"],
            result["execution_intent_bundle"]["bundle_file_sha256"],
        )
        self.assertEqual(result["candidate"]["execution_actor"],ACTOR)
        self.assertEqual(result["candidate"]["execution_actor_id"],ACTOR_ID)
        self.assertEqual(result["candidate"]["execution_max_requests"],1)
        self.assertEqual(
            result["candidate"]["request_plan_sha256"],
            result["execution_intent"]["request_plan_sha256"],
        )
        self.assertFalse(result["ledger_mutation_permitted"])

    def test_receipt_bound_to_wrong_execution_intent_is_rejected(self):
        args=list(good_inputs())
        receipt_zip=zip_receipt("0"*64)
        args[0]=metadata(receipt_zip)
        args[1]=receipt_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_receipt_bundle_is_required_and_hash_bound(self):
        args=list(good_inputs())
        tampered=(json.dumps({"tampered":True})+"\n").encode()
        tampered_zip=zip_bundle(tampered)
        args[4]=bundle_metadata(tampered_zip)
        args[5]=tampered_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_execution_intent_run_mismatch_rejected(self):
        args=list(good_inputs())
        args[6]["workflow_run"]["id"]=999
        args[6]["name"]="weatherapi-execution-intent-999"
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_execution_intent_commit_mismatch_rejected(self):
        args=list(good_inputs())
        args[6]["workflow_run"]["head_sha"]="c"*40
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_execution_intent_request_plan_mismatch_rejected(self):
        args=list(good_inputs())
        intent_marker_zip=zip_intent_marker(request_plan="0"*64)
        args[8]=intent_marker_metadata(intent_marker_zip)
        args[9]=intent_marker_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_execution_intent_actor_mismatch_rejected(self):
        args=list(good_inputs())
        intent_marker_zip=zip_intent_marker(actor="other-user")
        args[8]=intent_marker_metadata(intent_marker_zip)
        args[9]=intent_marker_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_execution_intent_bundle_hash_mismatch_rejected(self):
        args=list(good_inputs())
        tampered=(json.dumps({"tampered":True})+"\n").encode()
        tampered_zip=zip_intent_bundle(tampered)
        args[10]=intent_bundle_metadata(tampered_zip)
        args[11]=tampered_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_execution_intent_max_requests_must_be_exactly_one(self):
        bad_intent=execution_intent(max_requests_override=2)
        intent_zip=zip_intent(bad_intent)
        intent_marker_zip=zip_intent_marker(intent_value=bad_intent)
        args=list(good_inputs())
        args[6]=intent_metadata(intent_zip)
        args[7]=intent_zip
        args[8]=intent_marker_metadata(intent_marker_zip)
        args[9]=intent_marker_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

    def test_receipt_marker_request_plan_drift_rejected(self):
        args=list(good_inputs())
        marker=receipt_verification_marker()
        marker["request_plan_sha256"]="0"*64
        body={k:v for k,v in marker.items() if k!="marker_sha256"}
        marker["marker_sha256"]=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest()
        marker_zip=zip_one(
            "weatherapi_attestation_verification.json",
            (json.dumps(marker,sort_keys=True)+"\n").encode(),
        )
        args[2]=marker_metadata(marker_zip)
        args[3]=marker_zip
        with self.assertRaises(ValueError):
            ingest_github_artifact(
                *args,provider="WeatherAPI",repository=REPO,trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
