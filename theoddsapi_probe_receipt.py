"""Secret-free audit receipts for The Odds API /v4/sports probe."""
import hashlib
import json

ALLOWED_STATUS = {"PASS", "HOLD"}
ALLOWED_CATEGORIES = {
    "account_review_missing",
    "request_approval_missing",
    "secret_missing",
    "endpoint_mismatch",
    "http_status",
    "response_too_large",
    "malformed_json",
    "sports_contract",
    "quota_headers_invalid",
    "nonzero_usage_cost",
    "redirect_blocked",
    "missing_key",
    "invalid_key",
    "deactivated_key",
    "rate_limited",
    "out_of_usage_credits",
    "http_error",
    "transport_error",
    "unexpected_error",
    "authenticated_zero_credit_sports_schema",
}

def build_receipt(result, generated_at_utc, commit_sha="", run_id=""):
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

    body = {
        "schema_version": 1,
        "provider": "The Odds API",
        "endpoint": "https://api.the-odds-api.com/v4/sports",
        "status": status,
        "category": category,
        "detail": detail,
        "zero_usage_credit_required": True,
        "generated_at_utc": str(generated_at_utc),
        "git_commit": str(commit_sha),
        "github_run_id": str(run_id),
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt = dict(body)
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return receipt

def write_receipt(path, receipt):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
