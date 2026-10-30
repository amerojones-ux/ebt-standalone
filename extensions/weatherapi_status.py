"""Offline WeatherAPI.com response classification. No credentials or HTTP access.

The caller must not supply or log a raw request URL, API key, headers,
response body, exception text, or account identifiers.
"""
from __future__ import annotations

from typing import Optional

_ALLOWED_HTTP = frozenset({200, 400, 401, 403, 429, 500, 502, 503, 504})
_ERROR_CATEGORIES = {
    1002: "MISSING_CREDENTIAL",
    1003: "INVALID_REQUEST",
    1005: "INVALID_REQUEST",
    1006: "LOCATION_NOT_FOUND",
    2006: "INVALID_CREDENTIAL",
    2007: "QUOTA_EXCEEDED",
    2008: "CREDENTIAL_DISABLED",
    2009: "SUBSCRIPTION_DENIED",
    9000: "INVALID_REQUEST",
    9001: "INVALID_REQUEST",
    9999: "PROVIDER_ERROR",
}


def classify_weatherapi_response(http_status: int, error_code: Optional[int] = None,
                                 valid_current_shape: bool = False) -> dict[str, str]:
    """Classify already sanitized metadata. Never promotes a feed to usable."""
    if type(http_status) is not int or http_status not in _ALLOWED_HTTP:
        category = "UNEXPECTED_HTTP_STATUS"
    elif error_code is not None and (type(error_code) is not int):
        category = "INVALID_ERROR_METADATA"
    elif error_code is not None:
        category = _ERROR_CATEGORIES.get(error_code, "UNKNOWN_PROVIDER_ERROR")
    elif http_status == 200 and valid_current_shape is True:
        category = "REACHABLE_ONLY"
    elif http_status == 200:
        category = "UNEXPECTED_RESPONSE_SHAPE"
    elif http_status == 429:
        category = "RATE_LIMITED"
    elif http_status >= 500:
        category = "PROVIDER_ERROR"
    else:
        category = "UNCLASSIFIED_REJECTION"
    return {
        "provider": "weather",
        "connection": category,
        "forecast": "HOLD",
        "wager": "NOT APPROVED",
        "rights_verified": "false",
        "feed_verified": "false",
    }
