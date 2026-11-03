"""One-shot API-Sports NFL/NCAA /status authentication probe.

Network access occurs only after exact dual approval. The response body may
contain account/subscription information; it is validated in memory and never
printed or persisted.
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

from apisports_status_contract import validate_rate_headers, validate_status_payload
from provider_live_request_plan import build_request, get_plan, validate_response_url
from apisports_status_receipt import (
    ALLOWED_CATEGORIES,
    ALLOWED_STATUS,
    build_receipt,
    write_receipt,
)

REQUEST_APPROVAL="I_APPROVE_ONE_APISPORTS_STATUS_REQUEST"
ACCOUNT_REVIEW_APPROVAL="I_CONFIRM_APISPORTS_STATUS_PRIVACY_AND_RATE_LIMIT_REVIEWED"
PLAN=get_plan("API-Sports")
HOST=PLAN["host"]
PATH=PLAN["path"]
MAX_BODY=PLAN["max_body_bytes"]

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def _safe_result(status,category,detail=None):
    if status not in ALLOWED_STATUS:
        raise ValueError("result status is not receipt-compatible")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("result category is not receipt-compatible")
    if detail is not None and type(detail) is not int:
        raise ValueError("result detail is not receipt-compatible")
    out={"status":status,"category":category}
    if detail is not None:
        out["detail"]=detail
    return out

def _default_open(request,timeout):
    opener=urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
    )
    # API-Sports warns that frameworks may inject unsupported headers.
    # Remove urllib's default User-Agent so only the documented API key
    # application header is intentionally supplied.
    opener.addheaders=[]
    return opener.open(request,timeout=timeout)

def _classify_http_error(exc):
    if 300 <= exc.code < 400:
        return _safe_result("HOLD","redirect_blocked",int(exc.code))
    if exc.code == 401:
        return _safe_result("HOLD","auth_denied",401)
    if exc.code == 403:
        return _safe_result("HOLD","entitlement_denied",403)
    if exc.code == 429:
        return _safe_result("HOLD","rate_limited",429)
    return _safe_result("HOLD","http_status",int(exc.code))

def probe(confirm,account_review,opener=None):
    if account_review != ACCOUNT_REVIEW_APPROVAL:
        return _safe_result("HOLD","account_review_missing")
    if confirm != REQUEST_APPROVAL:
        return _safe_result("HOLD","request_approval_missing")

    key=os.environ.get("EBT_APISPORTS_API_KEY")
    if not key:
        return _safe_result("HOLD","secret_missing")

    try:
        request=build_request("API-Sports",key)
    except ValueError:
        return _safe_result("HOLD","endpoint_mismatch")
    url=request.full_url
    opener=_default_open if opener is None else opener

    try:
        response=opener(request,timeout=PLAN["timeout_seconds"])
        status=getattr(response,"status",None)
        final_url=getattr(response,"url",url)
        if validate_response_url(final_url,"API-Sports"):
            return _safe_result("HOLD","endpoint_mismatch")
        if type(status) is not int or status != 200:
            return _safe_result(
                "HOLD","http_status",status if type(status) is int else None
            )

        headers={
            str(k).lower():str(v)
            for k,v in getattr(response,"headers",{}).items()
        }
        rate_errors=validate_rate_headers(headers)
        if rate_errors:
            return _safe_result("HOLD","rate_headers_invalid",len(rate_errors))

        raw=response.read(MAX_BODY+1)
        if len(raw)>MAX_BODY:
            return _safe_result("HOLD","response_too_large")

        try:
            payload=json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError):
            return _safe_result("HOLD","malformed_json")

        status_errors=validate_status_payload(payload)
        if status_errors:
            return _safe_result("HOLD","status_contract",len(status_errors))

        return _safe_result("PASS","authenticated_status_schema")
    except urllib.error.HTTPError as exc:
        return _classify_http_error(exc)
    except (urllib.error.URLError,socket.timeout,TimeoutError):
        return _safe_result("HOLD","transport_error")
    except Exception:
        return _safe_result("HOLD","unexpected_error")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--confirm",required=True)
    parser.add_argument("--account-review",required=True)
    parser.add_argument("--receipt-path")
    args=parser.parse_args()

    result=probe(args.confirm,args.account_review)

    if args.receipt_path:
        receipt=build_receipt(
            result,
            datetime.now(timezone.utc).isoformat(),
            os.environ.get("GITHUB_SHA",""),
            os.environ.get("GITHUB_RUN_ID",""),
        )
        write_receipt(args.receipt_path,receipt)

    print("APISPORTS_STATUS_PROBE:",result["status"])
    print("CATEGORY:",result["category"])
    if "detail" in result:
        print("DETAIL:",result["detail"])
    print("Sanitized output only; no key, quota balance, account fields, headers, or response body logged.")
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":
    sys.exit(main())
