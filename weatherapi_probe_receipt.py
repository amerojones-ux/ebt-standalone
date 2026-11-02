"""Secret-free integrity-checksum receipts for the bounded WeatherAPI probe.

The SHA-256 field detects accidental or uncoordinated changes. It is not a
cryptographic signature and does not prove authenticity against an editor who
can recompute the checksum.
"""
import hashlib
import hmac
import json

ALLOWED_STATUS = {"PASS", "HOLD"}
ALLOWED_CATEGORIES = {
    "plan_review_missing",
    "request_approval_missing",
    "secret_missing",
    "endpoint_mismatch",
    "http_status",
    "response_too_large",
    "malformed_json",
    "data_contract",
    "redirect_blocked",
    "auth_missing_key",
    "auth_invalid_key",
    "quota_exceeded",
    "key_disabled",
    "entitlement_denied",
    "http_error",
    "transport_error",
    "unexpected_error",
    "authenticated_schema_fresh",
}
INTEGRITY_MODEL = "sha256-checksum-not-signature"
BODY_FIELDS = {
    "schema_version",
    "provider",
    "endpoint",
    "test_location",
    "status",
    "category",
    "detail",
    "generated_at_utc",
    "git_commit",
    "github_run_id",
    "integrity_model",
}
RECEIPT_FIELDS = BODY_FIELDS | {"receipt_sha256"}

def _validate_result(result):
    if not isinstance(result, dict):
        raise ValueError("result must be object")
    status = result.get("status")
    category = result.get("category")
    if status not in ALLOWED_STATUS:
        raise ValueError("invalid status")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("invalid category")
    detail = result.get("detail")
    if detail is not None and type(detail) is not int:
        raise ValueError("detail must be integer or null")
    return status, category, detail

def _canonical_body(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

def build_receipt(result, generated_at_utc, commit_sha="", run_id=""):
    status, category, detail = _validate_result(result)
    body = {
        "schema_version": 2,
        "provider": "WeatherAPI",
        "endpoint": "https://api.weatherapi.com/v1/current.json",
        "test_location": "Chicago",
        "status": status,
        "category": category,
        "detail": detail,
        "generated_at_utc": str(generated_at_utc),
        "git_commit": str(commit_sha),
        "github_run_id": str(run_id),
        "integrity_model": INTEGRITY_MODEL,
    }
    receipt = dict(body)
    receipt["receipt_sha256"] = hashlib.sha256(_canonical_body(body)).hexdigest()
    return receipt

def verify_receipt(receipt):
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        return False
    if receipt.get("schema_version") != 2:
        return False
    if receipt.get("provider") != "WeatherAPI":
        return False
    if receipt.get("endpoint") != "https://api.weatherapi.com/v1/current.json":
        return False
    if receipt.get("test_location") != "Chicago":
        return False
    if receipt.get("integrity_model") != INTEGRITY_MODEL:
        return False
    try:
        _validate_result({
            "status": receipt.get("status"),
            "category": receipt.get("category"),
            "detail": receipt.get("detail"),
        })
    except ValueError:
        return False
    expected = receipt.get("receipt_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    try:
        int(expected, 16)
    except ValueError:
        return False
    body = {key: receipt[key] for key in BODY_FIELDS}
    actual = hashlib.sha256(_canonical_body(body)).hexdigest()
    return hmac.compare_digest(actual, expected)

def write_receipt(path, receipt):
    if not verify_receipt(receipt):
        raise ValueError("receipt integrity validation failed")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
