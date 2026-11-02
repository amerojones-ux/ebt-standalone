"""Offline registry for prepared provider live-auth probes.

The registry distinguishes prepared/default-deny from approved/executed.
It never reads secrets or provider networks.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"

PROBES={
    "WeatherAPI":{
        "config":"config/weatherapi_execution_plan.json",
        "workflow":".github/workflows/weatherapi-live-probe.yml",
        "secret_name":"EBT_WEATHER_API_KEY",
        "receipt":"weatherapi_probe_receipt.json",
        "artifact_prefix":"weatherapi-probe-receipt",
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
        "review_phrase":"I_CONFIRM_THEODDSAPI_ACCOUNT_AND_ZERO_CREDIT_ENDPOINT_REVIEWED",
        "request_phrase":"I_APPROVE_ONE_THEODDSAPI_SPORTS_REQUEST",
        "hold_fields":{
            "network_enabled":False,
            "explicit_request_approval":False,
            "forecast_enabled":False,
            "request_count":0,
        },
    },
    "API-Sports":{
        "config":"config/apisports_status_auth.json",
        "workflow":".github/workflows/apisports-status-probe.yml",
        "secret_name":"EBT_APISPORTS_API_KEY",
        "receipt":"apisports_status_receipt.json",
        "artifact_prefix":"apisports-status-receipt",
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
        "github.ref == 'refs/heads/main'",
        'default: "NO"',
        "persist-credentials: false",
        spec["review_phrase"],
        spec["request_phrase"],
        "verify_receipt",
        "if: always()",
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
