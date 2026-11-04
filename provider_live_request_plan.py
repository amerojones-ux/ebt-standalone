"""Canonical one-shot live-provider request plans.

Pure request construction/validation. No network calls and no environment access.
Credential values are accepted by the builder but are never returned by validators.
"""
import hashlib
import json
import urllib.parse
import urllib.request

PLANS={
    "WeatherAPI":{
        "scheme":"https",
        "host":"api.weatherapi.com",
        "path":"/v1/current.json",
        "method":"GET",
        "credential_query_key":"key",
        "fixed_query":{"q":"Chicago"},
        "credential_header":None,
        "fixed_headers":{
            "accept":"application/json",
            "user-agent":"EBT-Black-Diamond/WeatherAPI-Auth-Probe",
        },
        "timeout_seconds":10,
        "max_requests":1,
        "allow_redirects":False,
        "retries":0,
        "max_body_bytes":32768,
    },
    "The Odds API":{
        "scheme":"https",
        "host":"api.the-odds-api.com",
        "path":"/v4/sports",
        "method":"GET",
        "credential_query_key":"apiKey",
        "fixed_query":{},
        "credential_header":None,
        "fixed_headers":{
            "accept":"application/json",
            "user-agent":"EBT-Black-Diamond/TheOddsAPI-Auth-Probe",
        },
        "timeout_seconds":10,
        "max_requests":1,
        "allow_redirects":False,
        "retries":0,
        "max_body_bytes":262144,
    },
    "TheRundown":{
        "scheme":"https",
        "host":"therundown.io",
        "path":"/api/v2/stats/sample",
        "method":"GET",
        "credential_query_key":None,
        "fixed_query":{},
        "credential_header":"X-TheRundown-Key",
        "fixed_headers":{
            "accept":"application/json",
        },
        "timeout_seconds":10,
        "max_requests":1,
        "allow_redirects":False,
        "retries":0,
        "max_body_bytes":524288,
    },
    "API-Sports":{
        "scheme":"https",
        "host":"v1.american-football.api-sports.io",
        "path":"/status",
        "method":"GET",
        "credential_query_key":None,
        "fixed_query":{},
        "credential_header":"x-apisports-key",
        "fixed_headers":{},
        "timeout_seconds":10,
        "max_requests":1,
        "allow_redirects":False,
        "retries":0,
        "max_body_bytes":65536,
    },
}

def get_plan(provider):
    plan=PLANS.get(provider)
    if plan is None:
        raise ValueError("unsupported provider request plan")
    return plan

def _normalize_headers(request):
    return {
        str(k).lower():str(v)
        for k,v in request.header_items()
    }

def _parse_query(query):
    pairs=urllib.parse.parse_qsl(
        query,keep_blank_values=True,strict_parsing=False
    )
    keys=[key for key,_ in pairs]
    if len(keys)!=len(set(keys)):
        raise ValueError("duplicate query key")
    return dict(pairs)

def build_request(provider, credential):
    plan=get_plan(provider)
    if not isinstance(credential,str) or not credential:
        raise ValueError("credential required")

    query=dict(plan["fixed_query"])
    credential_query_key=plan["credential_query_key"]
    if credential_query_key is not None:
        query[credential_query_key]=credential

    url=f'{plan["scheme"]}://{plan["host"]}{plan["path"]}'
    if query:
        url += "?" + urllib.parse.urlencode(query)

    headers=dict(plan["fixed_headers"])
    credential_header=plan["credential_header"]
    if credential_header is not None:
        headers[credential_header]=credential

    request=urllib.request.Request(
        url,
        method=plan["method"],
        headers=headers,
    )
    errors=validate_request(request,provider)
    if errors:
        raise ValueError("request plan mismatch")
    return request

def validate_request(request,provider):
    plan=get_plan(provider)
    errors=[]
    if not isinstance(request,urllib.request.Request):
        return ["request must be urllib Request"]

    if request.get_method()!=plan["method"]:
        errors.append("method mismatch")
    if request.data is not None:
        errors.append("request body forbidden")

    parsed=urllib.parse.urlsplit(request.full_url)
    if parsed.scheme!=plan["scheme"]:
        errors.append("scheme mismatch")
    if parsed.hostname!=plan["host"]:
        errors.append("host mismatch")
    if parsed.username is not None or parsed.password is not None:
        errors.append("userinfo forbidden")
    try:
        port=parsed.port
    except ValueError:
        port="invalid"
    if port is not None:
        errors.append("explicit port forbidden")
    if parsed.path!=plan["path"]:
        errors.append("path mismatch")
    if parsed.fragment:
        errors.append("fragment forbidden")

    try:
        query=_parse_query(parsed.query)
    except ValueError:
        query={}
        errors.append("query invalid")

    expected_query=set(plan["fixed_query"])
    credential_query_key=plan["credential_query_key"]
    if credential_query_key is not None:
        expected_query.add(credential_query_key)
    if set(query)!=expected_query:
        errors.append("query key set mismatch")
    for key,value in plan["fixed_query"].items():
        if query.get(key)!=value:
            errors.append("fixed query mismatch")
    if credential_query_key is not None and not query.get(credential_query_key):
        errors.append("credential query missing")

    headers=_normalize_headers(request)
    expected_headers=set(plan["fixed_headers"])
    credential_header=plan["credential_header"]
    if credential_header is not None:
        expected_headers.add(credential_header.lower())
    if set(headers)!=expected_headers:
        errors.append("header set mismatch")
    for key,value in plan["fixed_headers"].items():
        if headers.get(key.lower())!=value:
            errors.append("fixed header mismatch")
    if credential_header is not None and not headers.get(
        credential_header.lower()
    ):
        errors.append("credential header missing")

    return errors

def validate_response_url(url,provider):
    plan=get_plan(provider)
    if not isinstance(url,str) or not url:
        return ["response URL required"]
    parsed=urllib.parse.urlsplit(url)
    errors=[]
    if parsed.scheme!=plan["scheme"]:
        errors.append("scheme mismatch")
    if parsed.hostname!=plan["host"]:
        errors.append("host mismatch")
    if parsed.username is not None or parsed.password is not None:
        errors.append("userinfo forbidden")
    try:
        port=parsed.port
    except ValueError:
        port="invalid"
    if port is not None:
        errors.append("explicit port forbidden")
    if parsed.path!=plan["path"]:
        errors.append("path mismatch")
    if parsed.fragment:
        errors.append("fragment forbidden")
    return errors

def public_plan(provider):
    plan=get_plan(provider)
    return {
        "provider":provider,
        "scheme":plan["scheme"],
        "host":plan["host"],
        "path":plan["path"],
        "method":plan["method"],
        "query_keys":sorted(
            set(plan["fixed_query"]) |
            ({plan["credential_query_key"]} if plan["credential_query_key"] else set())
        ),
        "fixed_query":dict(plan["fixed_query"]),
        "header_names":sorted(
            set(plan["fixed_headers"]) |
            ({plan["credential_header"].lower()} if plan["credential_header"] else set())
        ),
        "timeout_seconds":plan["timeout_seconds"],
        "max_requests":plan["max_requests"],
        "allow_redirects":plan["allow_redirects"],
        "retries":plan["retries"],
        "max_body_bytes":plan["max_body_bytes"],
    }


def request_plan_sha256(provider):
    public=public_plan(provider)
    canonical=json.dumps(
        public,sort_keys=True,separators=(",",":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
