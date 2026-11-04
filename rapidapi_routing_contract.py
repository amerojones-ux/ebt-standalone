"""Offline RapidAPI routing/billing gate. No network or secrets."""
import re
import urllib.parse

HOST = re.compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", re.I)
PRICING_TYPES = {"UNKNOWN", "FREE", "PAY_PER_USE", "FREEMIUM", "PAID"}

AMBIGUOUS_PRODUCT_NAMES = {"", "all", "sports", "api", "unknown", "any"}

def validate_endpoint(value,host):
    if not isinstance(value,str) or not value:
        return ["exact endpoint required"]
    parsed=urllib.parse.urlsplit(value)
    errors=[]
    if parsed.scheme!="https":
        errors.append("endpoint must use https")
    if parsed.hostname!=host:
        errors.append("endpoint host mismatch")
    if parsed.username is not None or parsed.password is not None:
        errors.append("endpoint userinfo forbidden")
    try:
        port=parsed.port
    except ValueError:
        port="invalid"
    if port is not None:
        errors.append("endpoint explicit port forbidden")
    if not parsed.path or parsed.path=="/":
        errors.append("endpoint path required")
    if parsed.query:
        errors.append("endpoint query forbidden")
    if parsed.fragment:
        errors.append("endpoint fragment forbidden")
    return errors

def validate_plan(plan):
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be object"]

    if plan.get("provider") != "RapidAPI":
        errors.append("provider mismatch")
    if plan.get("secret_name") != "EBT_RAPIDAPI_API_KEY":
        errors.append("secret mapping mismatch")
    if plan.get("key_header") != "X-RapidAPI-Key":
        errors.append("key header mismatch")
    if plan.get("host_header") != "X-RapidAPI-Host":
        errors.append("host header mismatch")

    if plan.get("account_signin_confirmed") is not True:
        errors.append("account sign-in not confirmed")
    if plan.get("subscription_inventory_verified") is not True:
        errors.append("subscription inventory must be verified")
    if plan.get("route_binding_verified") is not True:
        errors.append("product-to-host route binding must be verified")

    product = plan.get("api_product")
    if not isinstance(product, str) or product.strip().casefold() in AMBIGUOUS_PRODUCT_NAMES:
        errors.append("exact API product required")

    host = plan.get("rapidapi_host")
    if not isinstance(host, str) or not HOST.fullmatch(host) or "." not in host:
        errors.append("exact RapidAPI host required")

    endpoint=plan.get("probe_endpoint")
    if plan.get("endpoint_reviewed") is True:
        errors.extend(validate_endpoint(endpoint,host))
    elif isinstance(endpoint,str) and endpoint.strip():
        errors.append("endpoint cannot be populated before review")

    pricing = plan.get("pricing_type")
    if pricing not in PRICING_TYPES:
        errors.append("invalid pricing type")
    if pricing == "UNKNOWN":
        errors.append("pricing type must be reviewed")

    if not isinstance(plan.get("plan_name"), str) or not plan.get("plan_name").strip():
        errors.append("plan name required")
    if not isinstance(plan.get("billing_object"), str) or not plan.get("billing_object").strip():
        errors.append("billing object required")

    for key in (
        "subscription_verified",
        "quota_reviewed",
        "overage_reviewed",
        "endpoint_reviewed",
    ):
        if plan.get(key) is not True:
            errors.append(key + " must be true")

    if plan.get("network_enabled") is not False:
        errors.append("network must remain disabled")
    if plan.get("request_count") != 0:
        errors.append("request count must be zero")
    if plan.get("forecast_enabled") is not False:
        errors.append("forecast must remain disabled")

    return errors

def can_prepare_live_probe(plan):
    """A reviewed route may be used to prepare code, never execute from this offline gate."""
    return not validate_plan(plan)

def can_execute_request(plan):
    """Execution is intentionally impossible in the offline routing contract."""
    return False
