"""Secret-free checksum receipts for TheRundown authenticated fixed sample probes."""
import hashlib
import hmac
import json

ALLOWED_STATUS={"PASS","HOLD"}
ALLOWED_CATEGORIES={
    "account_review_missing",
    "request_approval_missing",
    "secret_missing",
    "endpoint_mismatch",
    "http_status",
    "response_too_large",
    "content_length_invalid",
    "malformed_json",
    "empty_sample",
    "redirect_blocked",
    "auth_denied",
    "entitlement_denied",
    "rate_limited",
    "datapoint_header_invalid",
    "unexpected_datapoint_charge",
    "transport_error",
    "unexpected_error",
    "authenticated_zero_datapoint_sample_json",
}
INTEGRITY_MODEL="sha256-checksum-not-signature"
BODY_FIELDS={
    "schema_version","provider","endpoint","sample_only",
    "documented_zero_datapoint_endpoint","model_evidence_allowed",
    "status","category","detail","generated_at_utc","git_commit",
    "github_run_id","execution_intent_sha256","integrity_model",
}
RECEIPT_FIELDS=BODY_FIELDS|{"receipt_sha256"}

def _validate_result(result):
    if not isinstance(result,dict):
        raise ValueError("result must be object")
    status=result.get("status")
    category=result.get("category")
    detail=result.get("detail")
    if status not in ALLOWED_STATUS:
        raise ValueError("invalid status")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("invalid category")
    if detail is not None and type(detail) is not int:
        raise ValueError("detail must be integer or null")
    return status,category,detail

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def build_receipt(
    result,
    generated_at_utc,
    commit_sha="",
    run_id="",
    execution_intent_sha256="",
):
    status,category,detail=_validate_result(result)
    intent_sha=str(execution_intent_sha256).lower()
    if len(intent_sha)!=64:
        raise ValueError("execution intent SHA-256 required")
    try:
        int(intent_sha,16)
    except ValueError as exc:
        raise ValueError("execution intent SHA-256 invalid") from exc
    body={
        "schema_version":2,
        "provider":"TheRundown",
        "endpoint":"https://therundown.io/api/v2/stats/sample",
        "sample_only":True,
        "documented_zero_datapoint_endpoint":True,
        "model_evidence_allowed":False,
        "status":status,
        "category":category,
        "detail":detail,
        "generated_at_utc":str(generated_at_utc),
        "git_commit":str(commit_sha),
        "github_run_id":str(run_id),
        "execution_intent_sha256":intent_sha,
        "integrity_model":INTEGRITY_MODEL,
    }
    receipt=dict(body)
    receipt["receipt_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return receipt

def verify_receipt(receipt):
    if not isinstance(receipt,dict) or set(receipt)!=RECEIPT_FIELDS:
        return False
    if receipt.get("schema_version")!=2:
        return False
    if receipt.get("provider")!="TheRundown":
        return False
    if receipt.get("endpoint")!="https://therundown.io/api/v2/stats/sample":
        return False
    if receipt.get("sample_only") is not True:
        return False
    if receipt.get("documented_zero_datapoint_endpoint") is not True:
        return False
    if receipt.get("model_evidence_allowed") is not False:
        return False
    if receipt.get("integrity_model")!=INTEGRITY_MODEL:
        return False
    intent_sha=receipt.get("execution_intent_sha256")
    if not isinstance(intent_sha,str) or len(intent_sha)!=64:
        return False
    try:
        int(intent_sha,16)
    except ValueError:
        return False
    try:
        _validate_result({
            "status":receipt.get("status"),
            "category":receipt.get("category"),
            "detail":receipt.get("detail"),
        })
    except ValueError:
        return False
    expected=receipt.get("receipt_sha256")
    if not isinstance(expected,str) or len(expected)!=64:
        return False
    try:
        int(expected,16)
    except ValueError:
        return False
    body={key:receipt[key] for key in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)

def write_receipt(path,receipt):
    if not verify_receipt(receipt):
        raise ValueError("receipt integrity validation failed")
    with open(path,"w",encoding="utf-8") as handle:
        json.dump(receipt,handle,indent=2,sort_keys=True)
        handle.write("\n")
