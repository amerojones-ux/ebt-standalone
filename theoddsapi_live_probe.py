"""One-shot The Odds API /v4/sports authentication probe.

Network access occurs ONLY when BOTH approval phrases match exactly.
The approved endpoint is documented as zero usage credits.
Never logs API keys, full URLs, headers, response bodies, or provider messages.
"""
import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from theoddsapi_contract import validate_quota_headers, validate_sports
from provider_live_request_plan import build_request, get_plan, validate_response_url
from theoddsapi_probe_receipt import ALLOWED_CATEGORIES, ALLOWED_STATUS, build_receipt, write_receipt

REQUEST_APPROVAL = "I_APPROVE_ONE_THEODDSAPI_SPORTS_REQUEST"
ACCOUNT_REVIEW_APPROVAL = "I_CONFIRM_THEODDSAPI_ACCOUNT_AND_ZERO_CREDIT_ENDPOINT_REVIEWED"
PLAN = get_plan("The Odds API")
HOST = PLAN["host"]
PATH = PLAN["path"]
MAX_BODY = PLAN["max_body_bytes"]
MAX_ERROR_BODY = 4096

ERROR_CATEGORIES = {
    "MISSING_KEY": "missing_key",
    "INVALID_KEY": "invalid_key",
    "DEACTIVATED_KEY": "deactivated_key",
    "EXCEEDED_FREQ_LIMIT": "rate_limited",
    "OUT_OF_USAGE_CREDITS": "out_of_usage_credits",
}

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects before a second request can be issued."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def _safe_result(status, category, detail=None):
    if status not in ALLOWED_STATUS:
        raise ValueError("result status is not receipt-compatible")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("result category is not receipt-compatible")
    if detail is not None and type(detail) is not int:
        raise ValueError("result detail is not receipt-compatible")
    out = {"status": status, "category": category}
    if detail is not None:
        out["detail"] = detail
    return out

def _default_open(request, timeout):
    # Ignore runner/user proxy environment so query-string credentials go
    # directly to the allowlisted HTTPS provider host.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout)

def _extract_error_code(exc):
    try:
        raw = exc.read(MAX_ERROR_BODY + 1)
        if len(raw) > MAX_ERROR_BODY:
            return None
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        for field in ("error_code", "code"):
            value = payload.get(field)
            if isinstance(value, str) and value in ERROR_CATEGORIES:
                return value
        error = payload.get("error")
        if isinstance(error, dict):
            for field in ("error_code", "code"):
                value = error.get(field)
                if isinstance(value, str) and value in ERROR_CATEGORIES:
                    return value
    except Exception:
        return None
    return None

def _classify_http_error(exc):
    if 300 <= exc.code < 400:
        return _safe_result("HOLD", "redirect_blocked", int(exc.code))
    code = _extract_error_code(exc)
    if code is not None:
        return _safe_result("HOLD", ERROR_CATEGORIES[code])
    if exc.code == 429:
        return _safe_result("HOLD", "rate_limited", 429)
    return _safe_result("HOLD", "http_error", int(exc.code))

def probe(confirm, account_review, opener=None):
    if account_review != ACCOUNT_REVIEW_APPROVAL:
        return _safe_result("HOLD", "account_review_missing")
    if confirm != REQUEST_APPROVAL:
        return _safe_result("HOLD", "request_approval_missing")

    key = os.environ.get("EBT_THEODDS_API_KEY")
    if not key:
        return _safe_result("HOLD", "secret_missing")

    try:
        request = build_request("The Odds API", key)
    except ValueError:
        return _safe_result("HOLD", "endpoint_mismatch")
    url = request.full_url
    opener = _default_open if opener is None else opener

    try:
        response = opener(request, timeout=PLAN["timeout_seconds"])
        status = getattr(response, "status", None)
        final_url = getattr(response, "url", url)
        if validate_response_url(final_url, "The Odds API"):
            return _safe_result("HOLD", "endpoint_mismatch")
        if type(status) is not int or status != 200:
            return _safe_result(
                "HOLD", "http_status", status if type(status) is int else None
            )

        headers = {
            str(k).lower(): str(v)
            for k, v in getattr(response, "headers", {}).items()
        }
        quota_errors = validate_quota_headers(headers)
        if quota_errors:
            if any("zero usage cost" in error for error in quota_errors):
                return _safe_result("HOLD", "nonzero_usage_cost")
            return _safe_result("HOLD", "quota_headers_invalid", len(quota_errors))

        raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            return _safe_result("HOLD", "response_too_large")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _safe_result("HOLD", "malformed_json")

        sports_errors = validate_sports(payload)
        if sports_errors:
            return _safe_result("HOLD", "sports_contract", len(sports_errors))

        return _safe_result("PASS", "authenticated_zero_credit_sports_schema")
    except urllib.error.HTTPError as exc:
        return _classify_http_error(exc)
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        return _safe_result("HOLD", "transport_error")
    except Exception:
        return _safe_result("HOLD", "unexpected_error")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--account-review", required=True)
    parser.add_argument("--receipt-path")
    parser.add_argument("--execution-intent-sha256", required=True)
    args = parser.parse_args()

    result = probe(args.confirm, args.account_review)

    if args.receipt_path:
        receipt = build_receipt(
            result,
            datetime.now(timezone.utc).isoformat(),
            os.environ.get("GITHUB_SHA", ""),
            os.environ.get("GITHUB_RUN_ID", ""),
            args.execution_intent_sha256,
        )
        write_receipt(args.receipt_path, receipt)

    print("THEODDSAPI_LIVE_PROBE:", result["status"])
    print("CATEGORY:", result["category"])
    if "detail" in result:
        print("DETAIL:", result["detail"])
    print("Sanitized output only; no URL, key, headers, body, or provider message logged.")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
