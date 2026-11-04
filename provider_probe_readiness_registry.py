"""Offline registry for prepared provider live-auth probes.

The registry distinguishes prepared/default-deny from approved/executed.
It never reads secrets or provider networks.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"
SETUP_PYTHON_SHA="6d4fd22b20465ccc0f7354476588e8df7c9ca0e0"

PROBES={
    "WeatherAPI":{
        "config":"config/weatherapi_execution_plan.json",
        "workflow":".github/workflows/weatherapi-live-probe.yml",
        "secret_name":"EBT_WEATHER_API_KEY",
        "receipt":"weatherapi_probe_receipt.json",
        "artifact_prefix":"weatherapi-probe-receipt",
        "marker":"weatherapi_attestation_verification.json",
        "marker_prefix":"weatherapi-attestation-verification",
        "bundle":"weatherapi_attestation_bundle.json",
        "bundle_prefix":"weatherapi-attestation-bundle",
        "intent_prefix":"weatherapi-execution-intent",
        "intent_bundle_prefix":"weatherapi-execution-intent-attestation-bundle",
        "intent_marker_prefix":"weatherapi-execution-intent-attestation-verification",
        "signer_workflow":".github/workflows/weatherapi-live-probe.yml",
        "review_phrase":"I_CONFIRM_WEATHERAPI_PLAN_QUOTA_AND_BILLING_REVIEWED",
        "request_phrase":"I_APPROVE_ONE_WEATHERAPI_REQUEST",
        "hold_fields":{
            "network_enabled":False,
            "explicit_request_approval":False,
            "forecast_enabled":False,
            "max_requests":0,
        },
    },
    "The Odds API":{
        "config":"config/theoddsapi_auth.json",
        "workflow":".github/workflows/theoddsapi-live-probe.yml",
        "secret_name":"EBT_THEODDS_API_KEY",
        "receipt":"theoddsapi_probe_receipt.json",
        "artifact_prefix":"theoddsapi-probe-receipt",
        "marker":"theoddsapi_attestation_verification.json",
        "marker_prefix":"theoddsapi-attestation-verification",
        "bundle":"theoddsapi_attestation_bundle.json",
        "bundle_prefix":"theoddsapi-attestation-bundle",
        "intent_prefix":"theoddsapi-execution-intent",
        "intent_bundle_prefix":"theoddsapi-execution-intent-attestation-bundle",
        "intent_marker_prefix":"theoddsapi-execution-intent-attestation-verification",
        "signer_workflow":".github/workflows/theoddsapi-live-probe.yml",
        "review_phrase":"I_CONFIRM_THEODDSAPI_ACCOUNT_AND_ZERO_CREDIT_ENDPOINT_REVIEWED",
        "request_phrase":"I_APPROVE_ONE_THEODDSAPI_SPORTS_REQUEST",
        "hold_fields":{
            "network_enabled":False,
            "explicit_request_approval":False,
            "forecast_enabled":False,
            "request_count":0,
        },
    },
    "TheRundown":{
        "config":"config/therundown_access.json",
        "workflow":".github/workflows/therundown-live-probe.yml",
        "secret_name":"EBT_THERUNDOWN_API_KEY",
        "receipt":"therundown_probe_receipt.json",
        "artifact_prefix":"therundown-probe-receipt",
        "marker":"therundown_attestation_verification.json",
        "marker_prefix":"therundown-attestation-verification",
        "bundle":"therundown_attestation_bundle.json",
        "bundle_prefix":"therundown-attestation-bundle",
        "intent_prefix":"therundown-execution-intent",
        "intent_bundle_prefix":"therundown-execution-intent-attestation-bundle",
        "intent_marker_prefix":"therundown-execution-intent-attestation-verification",
        "signer_workflow":".github/workflows/therundown-live-probe.yml",
        "review_phrase":"I_CONFIRM_THERUNDOWN_PLAN_DATAPOINT_QUOTA_AND_OVERAGE_REVIEWED",
        "request_phrase":"I_APPROVE_ONE_THERUNDOWN_AUTHENTICATED_SNAPSHOT_REQUEST",
        "hold_fields":{
            "network_enabled":False,
            "authenticated_request_count":0,
            "forecast_enabled":False,
        },
    },
    "API-Sports":{
        "config":"config/apisports_status_auth.json",
        "workflow":".github/workflows/apisports-status-probe.yml",
        "secret_name":"EBT_APISPORTS_API_KEY",
        "receipt":"apisports_status_receipt.json",
        "artifact_prefix":"apisports-status-receipt",
        "marker":"apisports_attestation_verification.json",
        "marker_prefix":"apisports-attestation-verification",
        "bundle":"apisports_attestation_bundle.json",
        "bundle_prefix":"apisports-attestation-bundle",
        "intent_prefix":"apisports-execution-intent",
        "intent_bundle_prefix":"apisports-execution-intent-attestation-bundle",
        "intent_marker_prefix":"apisports-execution-intent-attestation-verification",
        "signer_workflow":".github/workflows/apisports-status-probe.yml",
        "review_phrase":"I_CONFIRM_APISPORTS_STATUS_PRIVACY_AND_RATE_LIMIT_REVIEWED",
        "request_phrase":"I_APPROVE_ONE_APISPORTS_STATUS_REQUEST",
        "hold_fields":{
            "network_enabled":False,
            "explicit_request_approval":False,
            "forecast_enabled":False,
            "request_count":0,
        },
    },
}

def _load_json(path):
    with (ROOT/path).open(encoding="utf-8") as handle:
        return json.load(handle)

def _read(path):
    return (ROOT/path).read_text(encoding="utf-8")

def assess_probe(name, *, json_loader=_load_json, text_loader=_read):
    spec=PROBES[name]
    errors=[]
    try:
        config=json_loader(spec["config"])
    except Exception:
        return {"provider":name,"status":"INVALID_HOLD","errors":["config unreadable"]}

    try:
        workflow=text_loader(spec["workflow"])
    except Exception:
        return {"provider":name,"status":"INVALID_HOLD","errors":["workflow unreadable"]}

    if config.get("secret_name")!=spec["secret_name"]:
        errors.append("secret mapping mismatch")

    for field,expected in spec["hold_fields"].items():
        value=config.get(field)
        if type(expected) is int:
            if type(value) is not int or value!=expected:
                errors.append(field+" hold mismatch")
        elif value is not expected:
            errors.append(field+" hold mismatch")

    required_workflow_fragments=[
        "workflow_dispatch:",
        "runs-on: ubuntu-24.04",
        "timeout-minutes: 5",
        "github.run_attempt == 1",
        "github.ref_protected == true",
        "concurrency:",
        "group: ebt-live-provider-probes",
        "cancel-in-progress: false",
        "github.ref == 'refs/heads/main'",
        'default: "NO"',
        "ref: ${{ github.sha }}",
        "Verify immutable source checkout",
        'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
        'test -z "$(git status --porcelain)"',
        "persist-credentials: false",
        spec["review_phrase"],
        spec["request_phrase"],
        "verify_receipt",
        "actions/setup-python@"+SETUP_PYTHON_SHA,
        'python-version: "3.13"',
        "check-latest: false",
        "id: toolchain",
        'echo "toolchain_verified=1" >> "$GITHUB_OUTPUT"',
        "if: steps.toolchain.outputs.toolchain_verified == '1'",
        "gh attestation verify --help",
        "Build sanitized one-shot execution intent",
        "provider_execution_intent_cli.py",
        "--review-authorization",
        "--request-authorization",
        '--workflow-run-attempt "$GITHUB_RUN_ATTEMPT"',
        "subject-path: provider_execution_intent.json",
        "id: attest_intent",
        "id: verify_intent",
        "gh attestation verify provider_execution_intent.json",
        "/tmp/execution-intent-local-verification.json",
        "/tmp/execution-intent-api-verification.json",
        '"request_plan_sha256":intent["request_plan_sha256"]',
        '"workflow_run_attempt": intent["workflow_run_attempt"]',
        "verify_execution_intent_marker",
        "execution intent marker verification failed",
        '"max_requests":intent["max_requests"]',
        'echo "intent_verified=1" >> "$GITHUB_OUTPUT"',
        'handle.write("intent_sha256="+intent["intent_sha256"]+"\\n")',
        '--execution-intent-sha256 "${{ steps.intent.outputs.intent_sha256 }}"',
        "name: "+spec["intent_prefix"]+"-${{ github.run_id }}",
        "name: "+spec["intent_bundle_prefix"]+"-${{ github.run_id }}",
        "name: "+spec["intent_marker_prefix"]+"-${{ github.run_id }}",
        "steps.verify_intent.outputs.intent_verified == '1'",
        "id: probe",
        'echo "receipt_verified=$receipt_ok" >> "$GITHUB_OUTPUT"',
        "  id-token: write",
        "  attestations: write",
        "  artifact-metadata: write",
        "if: always() && steps.probe.outputs.receipt_verified == '1'",
        "actions/attest@"+ATTEST_SHA,
        "subject-path: "+spec["receipt"],
        "id: verify_attestation",
        "ATTESTATION_BUNDLE_PATH: ${{ steps.attest.outputs.bundle-path }}",
        'test -f "$ATTESTATION_BUNDLE_PATH"',
        'gh attestation verify "$RECEIPT_FILE"',
        '--bundle "$ATTESTATION_BUNDLE_PATH"',
        '--repo "$GITHUB_REPOSITORY"',
        '--signer-workflow "$GITHUB_REPOSITORY/$SIGNER_WORKFLOW"',
        '--source-ref "refs/heads/main"',
        '--source-digest "$GITHUB_SHA"',
        "/tmp/attestation-local-verification.json",
        "/tmp/attestation-api-verification.json",
        '"schema_version": 4',
        '"verification_modes": ["local_bundle", "github_api"]',
        '"attestation_bundle_sha256": bundle_sha256',
        '"runner_label": os.environ["RUNNER_LABEL"]',
        '"python_version": os.environ["TOOLCHAIN_PYTHON_VERSION"]',
        '"gh_version": os.environ["TOOLCHAIN_GH_VERSION"]',
        '"setup_python_sha": os.environ["SETUP_PYTHON_SHA"]',
        '"request_plan_sha256": request_plan_sha256(',
        '"required_attestation_flags": [',
        "RUNNER_LABEL: ubuntu-24.04",
        "SETUP_PYTHON_SHA: "+SETUP_PYTHON_SHA,
        "TOOLCHAIN_PYTHON_VERSION: ${{ steps.toolchain.outputs.python_version }}",
        "TOOLCHAIN_GH_VERSION: ${{ steps.toolchain.outputs.gh_version }}",
        "BUNDLE_EXPORT_FILE: "+spec["bundle"],
        'cp -- "$ATTESTATION_BUNDLE_PATH" "$BUNDLE_EXPORT_FILE"',
        'test -s "$BUNDLE_EXPORT_FILE"',
        "name: "+spec["bundle_prefix"]+"-${{ github.run_id }}",
        "path: "+spec["bundle"],
        "SIGNER_WORKFLOW: "+spec["signer_workflow"],
        "provider_attestation_verification_marker",
        "verify_marker",
        "receipt attestation marker verification failed",
        'echo "attestation_verified=1" >> "$GITHUB_OUTPUT"',
        "name: "+spec["marker_prefix"]+"-${{ github.run_id }}",
        "path: "+spec["marker"],
        "if-no-files-found: error",
        "actions/upload-artifact@"+UPLOAD_SHA,
        "name: "+spec["artifact_prefix"]+"-${{ github.run_id }}",
        "path: "+spec["receipt"],
        "retention-days: 7",
        "if-no-files-found: ignore",
    ]
    for fragment in required_workflow_fragments:
        if fragment not in workflow:
            errors.append("workflow invariant missing: "+fragment)

    forbidden=[
        "schedule:",
        "\npush:",
        "\n  push:",
        "pull_request:",
        "retention-days: 90",
        "cancel-in-progress: true",
        "ref: main",
    ]
    for fragment in forbidden:
        if fragment in workflow:
            errors.append("forbidden workflow behavior: "+fragment)

    if errors:
        status="INVALID_HOLD"
    else:
        status="PREPARED_DEFAULT_DENY"

    return {
        "provider":name,
        "status":status,
        "manual_dispatch_required":True,
        "committed_request_approval":False,
        "execution_claimed":False,
        "artifact_retention_days":7,
        "signed_provenance_required":True,
        "cryptographic_verification_required":True,
        "exact_bundle_verification_required":True,
        "github_api_verification_required":True,
        "persisted_attestation_bundle_required":True,
        "runner_pinned":True,
        "python_toolchain_pinned":True,
        "attestation_cli_capability_preflight_required":True,
        "toolchain_fingerprint_bound":True,
        "request_plan_fingerprint_bound":True,
        "signed_presecret_execution_intent_required":True,
        "execution_intent_dual_attestation_verification_required":True,
        "receipt_execution_intent_direct_binding_required":True,
        "first_workflow_attempt_only_required":True,
        "global_live_probe_serialization_required":True,
        "immutable_dispatch_commit_checkout_required":True,
        "protected_ref_runtime_gate_required":True,
        "signed_first_attempt_binding_required":True,
        "generated_marker_self_verification_required":True,
        "errors":errors,
    }

def assess_all():
    results=[assess_probe(name) for name in PROBES]
    return {
        "status":"PREPARED_DEFAULT_DENY" if all(
            r["status"]=="PREPARED_DEFAULT_DENY" for r in results
        ) else "INVALID_HOLD",
        "probe_count":len(results),
        "probes":results,
    }
