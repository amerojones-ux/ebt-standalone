"""Offline-only request planning for WeatherAPI.com; never accepts a key.

A credentialed query-string request must only be assembled inside an independently
approved protected runner. This module performs no network or secret operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

_HOST = "api.weatherapi.com"
_PATH = "/v1/current.json"


@dataclass(frozen=True)
class WeatherRequestPlan:
    provider: str
    host: str
    path: str
    method: str
    location: str
    timeout_seconds: int
    max_response_bytes: int
    redirect_allowed: bool
    forecast: str
    wager: str


def plan_weatherapi_current(endpoint: str, *, location: str = "London",
                            reviewed_endpoint: bool = False) -> WeatherRequestPlan:
    """Validate non-secret configuration and return a non-executable plan."""
    if not isinstance(endpoint, str):
        raise ValueError("invalid endpoint")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError:
        raise ValueError("invalid endpoint") from None
    if (parsed.scheme != "https" or parsed.hostname != _HOST
            or parsed.path != _PATH or parsed.query or parsed.fragment
            or parsed.username is not None or parsed.password is not None
            or port not in (None, 443) or not reviewed_endpoint):
        raise ValueError("endpoint not independently approved")
    if endpoint != f"https://{_HOST}{_PATH}":
        raise ValueError("noncanonical endpoint")
    if location != "London":
        raise ValueError("unreviewed smoke-test location")
    return WeatherRequestPlan(
        provider="weather", host=_HOST, path=_PATH, method="GET",
        location=location, timeout_seconds=5, max_response_bytes=65536,
        redirect_allowed=False, forecast="HOLD", wager="NOT APPROVED")
