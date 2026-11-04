"""One-shot TheRundown authenticated fixed sample probe.

The endpoint is documented as an authenticated, fixed complete-game stats
sample costing zero data points. A PASS proves only key authentication and
sample-route JSON access. It does not prove current/live data, stats
entitlement, sportsbook coverage, freshness, or model-evidence eligibility.
"""
import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from provider_live_request_plan import build_request, get_plan, validate_response_url
from therundown_probe_receipt import (
    ALLOWED_CATEGORIES,
    ALLOWED_STATUS,
    build_receipt,
    write_receipt,
)

REQUEST_APPROVAL="I_APPROVE_ONE_THERUNDOWN_AUTHENTICATED_SNAPSHOT_REQUEST"
ACCOUNT_REVIEW_APPROVAL=(
    "I_CONFIRM_THERUNDOWN_PLAN_DATAPOINT_QUOTA_AND_OVERAGE_REVIEWED"
)
PLAN=get_plan("TheRundown")
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

def _content_length(headers):
    raw=headers.get("content-length")
    if raw is None or not str(raw).strip():
        return None
    try:
        value=int(str(raw).strip())
    except ValueError:
        raise ValueError("invalid content length")
    if value<0:
        raise ValueError("invalid content length")
    return value

def _datapoint_charge(headers):
    raw=headers.get("x-datapoints")
    if raw is None or not str(raw).strip():
        return None
    try:
        value=int(str(raw).strip())
    except ValueError:
        raise ValueError("invalid datapoint header")
    if value<0:
        raise ValueError("invalid datapoint header")
    return value

def probe(confirm,account_review,opener=None):
    if account_review != ACCOUNT_REVIEW_APPROVAL:
        return _safe_result("HOLD","account_review_missing")
    if confirm != REQUEST_APPROVAL:
        return _safe_result("HOLD","request_approval_missing")

    key=os.environ.get("EBT_THERUNDOWN_API_KEY")
    if not key:
        return _safe_result("HOLD","secret_missing")

    try:
        request=build_request("TheRundown",key)
    except ValueError:
        return _safe_result("HOLD","endpoint_mismatch")

    url=request.full_url
    opener=_default_open if opener is None else opener

    try:
        response=opener(request,timeout=PLAN["timeout_seconds"])
        status=getattr(response,"status",None)
        final_url=getattr(response,"url",url)
        if validate_response_url(final_url,"TheRundown"):
            return _safe_result("HOLD","endpoint_mismatch")
        if type(status) is not int or status != 200:
            return _safe_result(
                "HOLD","http_status",status if type(status) is int else None
            )

        headers={
            str(k).lower():str(v)
            for k,v in getattr(response,"headers",{}).items()
        }
        try:
            charge=_datapoint_charge(headers)
        except ValueError:
            return _safe_result("HOLD","datapoint_header_invalid")
        if charge not in (None,0):
            return _safe_result("HOLD","unexpected_datapoint_charge",charge)

        try:
            declared_length=_content_length(headers)
        except ValueError:
            return _safe_result("HOLD","response_too_large",MAX_BODY+1)
        if declared_length is not None and declared_length>MAX_BODY:
            return _safe_result("HOLD","response_too_large",declared_length)

        raw=response.read(MAX_BODY+1)
        if len(raw)>MAX_BODY:
            return _safe_result("HOLD","response_too_large",len(raw))
        try:
            payload=json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError):
            return _safe_result("HOLD","malformed_json")
        if not isinstance(payload,(dict,list)) or len(payload)==0:
            return _safe_result("HOLD","empty_sample")

        return _safe_result("PASS","authenticated_zero_datapoint_sample_json")
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
    parser.add_argument("--execution-intent-sha256",required=True)
    args=parser.parse_args()

    result=probe(args.confirm,args.account_review)

    if args.receipt_path:
        receipt=build_receipt(
            result,
            datetime.now(timezone.utc).isoformat(),
            os.environ.get("GITHUB_SHA",""),
            os.environ.get("GITHUB_RUN_ID",""),
            args.execution_intent_sha256,
        )
        write_receipt(args.receipt_path,receipt)

    print("THERUNDOWN_LIVE_PROBE:",result["status"])
    print("CATEGORY:",result["category"])
    if "detail" in result:
        print("DETAIL:",result["detail"])
    print(
        "Sanitized output only; no API key, response body, headers, "
        "usage balance, or account fields logged."
    )
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":
    sys.exit(main())
