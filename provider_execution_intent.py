"""Signed-intent contract for one-shot provider probes.

Pure JSON construction/verification. No environment access, no secrets, no network.
"""
from datetime import datetime
import hashlib
import hmac
import json
import re

from provider_live_request_plan import request_plan_sha256

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
ACTOR=re.compile(r"^[A-Za-z0-9-]+$")
ACTOR_ID=re.compile(r"^[0-9]+$")
REPOSITORY="amerojones-ux/ebt-standalone"

CONTRACTS={
    "WeatherAPI":{
        "workflow":".github/workflows/weatherapi-live-probe.yml",
        "review_authorization":"I_CONFIRM_WEATHERAPI_PLAN_QUOTA_AND_BILLING_REVIEWED",
        "request_authorization":"I_APPROVE_ONE_WEATHERAPI_REQUEST",
    },
    "The Odds API":{
        "workflow":".github/workflows/theoddsapi-live-probe.yml",
        "review_authorization":"I_CONFIRM_THEODDSAPI_ACCOUNT_AND_ZERO_CREDIT_ENDPOINT_REVIEWED",
        "request_authorization":"I_APPROVE_ONE_THEODDSAPI_SPORTS_REQUEST",
    },
    "API-Sports":{
        "workflow":".github/workflows/apisports-status-probe.yml",
        "review_authorization":"I_CONFIRM_APISPORTS_STATUS_PRIVACY_AND_RATE_LIMIT_REVIEWED",
        "request_authorization":"I_APPROVE_ONE_APISPORTS_STATUS_REQUEST",
    },
}

BODY_FIELDS={
    "schema_version","provider","repository","workflow_run_id","workflow_run_attempt",
    "source_commit","source_ref","signer_workflow",
    "actor","actor_id","generated_at_utc",
    "review_authorization","request_authorization",
    "request_plan_sha256","max_requests",
    "network_scope","ledger_mutation_permitted",
    "readiness_mutation_permitted","forecast_activation_permitted",
}
ALL_FIELDS=BODY_FIELDS|{"intent_sha256"}

def _parse_time(value):
    if not isinstance(value,str) or not value.strip():
        return None
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def build_execution_intent(
    *,
    provider,
    repository,
    workflow_run_id,
    workflow_run_attempt,
    source_commit,
    source_ref,
    signer_workflow,
    actor,
    actor_id,
    generated_at_utc,
    review_authorization,
    request_authorization,
):
    contract=CONTRACTS.get(provider)
    if contract is None:
        raise ValueError("unsupported provider")
    body={
        "schema_version":2,
        "provider":provider,
        "repository":repository,
        "workflow_run_id":workflow_run_id,
        "workflow_run_attempt":workflow_run_attempt,
        "source_commit":source_commit.lower() if isinstance(source_commit,str) else source_commit,
        "source_ref":source_ref,
        "signer_workflow":signer_workflow,
        "actor":actor,
        "actor_id":actor_id,
        "generated_at_utc":generated_at_utc,
        "review_authorization":review_authorization,
        "request_authorization":request_authorization,
        "request_plan_sha256":request_plan_sha256(provider),
        "max_requests":1,
        "network_scope":"one-shot-authentication-probe",
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    }
    result=dict(body)
    result["intent_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    if not verify_execution_intent(result):
        raise ValueError("execution intent contract invalid")
    return result

def verify_execution_intent(value):
    if not isinstance(value,dict) or set(value)!=ALL_FIELDS:
        return False
    provider=value.get("provider")
    contract=CONTRACTS.get(provider)
    if contract is None:
        return False
    if value.get("schema_version")!=2:
        return False
    if value.get("repository")!=REPOSITORY:
        return False
    if not RUN_ID.fullmatch(value.get("workflow_run_id","")):
        return False
    if type(value.get("workflow_run_attempt")) is not int or value["workflow_run_attempt"]!=1:
        return False
    if not SHA40.fullmatch(value.get("source_commit","")):
        return False
    if value.get("source_ref")!="refs/heads/main":
        return False
    if value.get("signer_workflow")!=contract["workflow"]:
        return False
    if not ACTOR.fullmatch(value.get("actor","")):
        return False
    if not ACTOR_ID.fullmatch(value.get("actor_id","")):
        return False
    if _parse_time(value.get("generated_at_utc")) is None:
        return False
    if value.get("review_authorization")!=contract["review_authorization"]:
        return False
    if value.get("request_authorization")!=contract["request_authorization"]:
        return False
    if value.get("request_plan_sha256")!=request_plan_sha256(provider):
        return False
    if type(value.get("max_requests")) is not int or value["max_requests"]!=1:
        return False
    if value.get("network_scope")!="one-shot-authentication-probe":
        return False
    if value.get("ledger_mutation_permitted") is not False:
        return False
    if value.get("readiness_mutation_permitted") is not False:
        return False
    if value.get("forecast_activation_permitted") is not False:
        return False
    expected=value.get("intent_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={key:value[key] for key in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)
