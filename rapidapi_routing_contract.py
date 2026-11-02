"""Offline RapidAPI routing/billing gate. No network or secrets."""
import re

HOST = re.compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", re.I)
PRICING_TYPES = {"UNKNOWN", "FREE", "PAY_PER_USE", "FREEMIUM", "PAID"}

AMBIGUOUS_PRODUCT_NAMES = {"", "all", "sports", "api", "unknown", "any"}

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

    product = plan.get("api_product")
    if not isinstance(product, str) or product.strip().casefold() in AMBIGUOUS_PRODUCT_NAMES:
        errors.append("exact API product required")

    host = plan.get("rapidapi_host")
    if not isinstance(host, str) or not HOST.fullmatch(host) or "." not in host:
        errors.append("exact RapidAPI host required")

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
