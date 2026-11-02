"""One-shot WeatherAPI authentication probe.

Network access occurs ONLY when --confirm exactly matches the approval phrase.
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

APPROVAL = "I_APPROVE_ONE_WEATHERAPI_REQUEST"
HOST = "api.weatherapi.com"
PATH = "/v1/current.json"
LOCATION = "Chicago"
MAX_BODY = 32768

def _safe_result(status, category, detail=None):
    out = {"status": status, "category": category}
    if detail is not None:
        out["detail"] = detail
    return out

def probe(confirm, opener=urllib.request.urlopen, now_epoch=None):
    if confirm != APPROVAL:
        return _safe_result("HOLD", "approval_missing")
    key = os.environ.get("EBT_WEATHER_API_KEY")
    if not key:
        return _safe_result("HOLD", "secret_missing")

    query = urllib.parse.urlencode({"key": key, "q": LOCATION, "aqi": "no"})
    url = f"https://{HOST}{PATH}?{query}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "EBT-Black-Diamond/WeatherAPI-Auth-Probe"},
    )
    try:
        response = opener(request, timeout=10)
        status = getattr(response, "status", None)
        final_url = getattr(response, "url", url)
        parsed = urllib.parse.urlparse(final_url)
        if parsed.scheme != "https" or parsed.hostname != HOST or parsed.path != PATH:
            return _safe_result("HOLD", "redirect_or_endpoint_mismatch")
        if status != 200:
            return _safe_result("HOLD", "http_status", int(status) if isinstance(status, int) else None)
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
        return _safe_result("HOLD", "http_error", int(exc.code))
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        return _safe_result("HOLD", "transport_error")
    except Exception:
        return _safe_result("HOLD", "unexpected_error")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    result = probe(args.confirm)
    print("WEATHERAPI_LIVE_PROBE:", result["status"])
    print("CATEGORY:", result["category"])
    if "detail" in result:
        print("DETAIL:", result["detail"])
    print("Sanitized output only; no URL, key, headers, or response body logged.")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
