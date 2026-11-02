"""Offline API-Sports NFL/NCAA /status contract. No network or secrets."""

RATE_HEADERS = (
    "x-ratelimit-requests-limit",
    "x-ratelimit-requests-remaining",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
)

def validate_rate_headers(headers):
    """Validate documented daily/minute rate-limit headers without exposing values."""
    if not isinstance(headers, dict):
        return ["headers must be object"]

    errors = []
    parsed = {}
    for name in RATE_HEADERS:
        value = headers.get(name)
        try:
            number = int(value)
        except (TypeError, ValueError):
            errors.append(name + " missing or invalid")
            continue
        if number < 0:
            errors.append(name + " must be nonnegative")
            continue
        parsed[name] = number

    daily_limit = parsed.get("x-ratelimit-requests-limit")
    daily_remaining = parsed.get("x-ratelimit-requests-remaining")
    minute_limit = parsed.get("x-ratelimit-limit")
    minute_remaining = parsed.get("x-ratelimit-remaining")

    if daily_limit is not None and daily_remaining is not None:
        if daily_remaining > daily_limit:
            errors.append("daily remaining exceeds limit")
    if minute_limit is not None and minute_remaining is not None:
        if minute_remaining > minute_limit:
            errors.append("minute remaining exceeds limit")

    return errors


def validate_status_payload(payload):
    """Validate only generic envelope fields; never inspect account PII."""
    if not isinstance(payload, dict):
        return ["response must be object"]

    errors = []
    provider_errors = payload.get("errors")
    if provider_errors not in (None, {}, []):
        errors.append("provider reports errors")

    response = payload.get("response")
    if not isinstance(response, dict) or not response:
        errors.append("non-empty response object required")

    results = payload.get("results")
    if results is not None:
        if type(results) is not int or results < 0:
            errors.append("results must be nonnegative integer")

    return errors
