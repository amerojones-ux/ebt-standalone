"""Offline schema checks for The Odds API v4 /sports response. No network."""
import re

SPORT_KEY = re.compile(r"^[a-z0-9_]+$")

def validate_sports(payload):
    errors = []
    if not isinstance(payload, list):
        return ["response must be a list"]
    if not payload:
        return ["sports list must not be empty"]

    seen = set()
    for i, item in enumerate(payload):
        prefix = f"item[{i}]"
        if not isinstance(item, dict):
            errors.append(prefix + " must be object")
            continue

        key = item.get("key")
        group = item.get("group")
        title = item.get("title")
        active = item.get("active")
        has_outrights = item.get("has_outrights")

        if not isinstance(key, str) or not SPORT_KEY.fullmatch(key):
            errors.append(prefix + " invalid key")
        elif key in seen:
            errors.append(prefix + " duplicate key")
        else:
            seen.add(key)

        if not isinstance(group, str) or not group.strip():
            errors.append(prefix + " invalid group")
        if not isinstance(title, str) or not title.strip():
            errors.append(prefix + " invalid title")
        if type(active) is not bool:
            errors.append(prefix + " active must be boolean")
        if type(has_outrights) is not bool:
            errors.append(prefix + " has_outrights must be boolean")

    return errors


def validate_quota_headers(headers):
    """Validate documented quota headers without assuming a plan size."""
    errors = []
    if not isinstance(headers, dict):
        return ["headers must be object"]

    for name in ("x-requests-remaining", "x-requests-used", "x-requests-last"):
        value = headers.get(name)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            errors.append(name + " missing or invalid")
            continue
        if parsed < 0:
            errors.append(name + " must be nonnegative")

    last = headers.get("x-requests-last")
    try:
        if int(last) != 0:
            errors.append("sports endpoint must report zero usage cost")
    except (TypeError, ValueError):
        pass

    return errors
