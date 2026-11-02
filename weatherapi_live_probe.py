"""One-shot WeatherAPI authentication probe with dual consent.

Network access occurs ONLY when BOTH approval phrases match exactly.
Never logs API keys, URLs, headers, or response bodies.
"""
import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

from weatherapi_contract import validate_current

REQUEST_APPROVAL = "I_APPROVE_ONE_WEATHERAPI_REQUEST"
PLAN_REVIEW_APPROVAL = "I_CONFIRM_WEATHERAPI_PLAN_QUOTA_AND_BILLING_REVIEWED"
HOST = "api.weatherapi.com"
PATH = "/v1/current.json"
LOCATION = "Chicago"
MAX_BODY = 32768
MAX_ERROR_BODY = 4096

WEATHERAPI_ERROR_CATEGORIES = {
    1002: "auth_missing_key",
    2006: "auth_invalid_key",
    2007: "quota_exceeded",
    2008: "key_disabled",
    2009: "entitlement_denied",
}

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects before a second HTTP request can be issued."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def _safe_result(status, category, detail=None):
    out = {"status": status, "category": category}
    if detail is not None:
        out["detail"] = detail
    return out

def _default_open(request, timeout):
    opener = urllib.request.build_opener(NoRedirectHandler())
    return opener.open(request, timeout=timeout)


def _classify_http_error(exc):
    """Extract only WeatherAPI numeric error codes; never return provider messages."""
    if 300 <= exc.code < 400:
        return _safe_result("HOLD", "redirect_blocked", int(exc.code))

    provider_code = None
    try:
        raw = exc.read(MAX_ERROR_BODY + 1)
        if len(raw) <= MAX_ERROR_BODY:
            payload = json.loads(raw.decode("utf-8"))
            error = payload.get("error") if isinstance(payload, dict) else None
            code = error.get("code") if isinstance(error, dict) else None
            if type(code) is int:
                provider_code = code
    except Exception:
        provider_code = None

    category = WEATHERAPI_ERROR_CATEGORIES.get(provider_code, "http_error")
    detail = provider_code if provider_code is not None else int(exc.code)
    return _safe_result("HOLD", category, detail)

def probe(confirm, plan_review, opener=None, now_epoch=None):
    if plan_review != PLAN_REVIEW_APPROVAL:
        return _safe_result("HOLD", "plan_review_missing")
    if confirm != REQUEST_APPROVAL:
        return _safe_result("HOLD", "request_approval_missing")

    key = os.environ.get("EBT_WEATHER_API_KEY")
    if not key:
        return _safe_result("HOLD", "secret_missing")

    query = urllib.parse.urlencode({"key": key, "q": LOCATION, "aqi": "no"})
    url = f"https://{HOST}{PATH}?{query}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "EBT-Black-Diamond/WeatherAPI-Auth-Probe",
        },
    )
    opener = _default_open if opener is None else opener
    try:
        response = opener(request, timeout=10)
        status = getattr(response, "status", None)
        final_url = getattr(response, "url", url)
        parsed = urllib.parse.urlparse(final_url)
        if parsed.scheme != "https" or parsed.hostname != HOST or parsed.path != PATH:
            return _safe_result("HOLD", "endpoint_mismatch")
        if type(status) is not int or status != 200:
            return _safe_result(
                "HOLD", "http_status", status if type(status) is int else None
            )

        raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            return _safe_result("HOLD", "response_too_large")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _safe_result("HOLD", "malformed_json")

        errors = validate_current(payload, LOCATION, now_epoch)
        if errors:
            return _safe_result("HOLD", "data_contract", len(errors))

        return _safe_result("PASS", "authenticated_schema_fresh")
    except urllib.error.HTTPError as exc:
        return _classify_http_error(exc)
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        return _safe_result("HOLD", "transport_error")
    except Exception:
        return _safe_result("HOLD", "unexpected_error")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--plan-review", required=True)
    args = parser.parse_args()

    result = probe(args.confirm, args.plan_review)
    print("WEATHERAPI_LIVE_PROBE:", result["status"])
    print("CATEGORY:", result["category"])
    if "detail" in result:
        print("DETAIL:", result["detail"])
    print("Sanitized output only; no URL, key, headers, or response body logged.")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
