"""Explicit, read-only API health probes with strict endpoint allowlisting.

No provider endpoint is hardcoded: operator supplies a pre-reviewed HTTPS host/path
and auth scheme in a private deployment. No raw response body, URL, key or headers
are returned/logged. This module NEVER authorizes forecasting or ingestion.
"""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from extensions.provider_gateway import PROVIDERS, ProviderGateError

_ALLOWED_AUTH = frozenset({"x-api-key", "authorization-bearer"})
_ALLOWED_CONTENT_TYPES = ("application/json", "application/problem+json")


@dataclass(frozen=True)
class ProbeSpec:
    provider: str
    endpoint: str
    expected_hostname: str
    auth_scheme: str
    timeout_seconds: float = 5.0


def _validate_spec(spec: ProbeSpec) -> str:
    if not isinstance(spec, ProbeSpec) or spec.provider not in PROVIDERS:
        raise ProviderGateError("invalid provider probe")
    if spec.auth_scheme not in _ALLOWED_AUTH:
        raise ProviderGateError("unsupported authentication scheme")
    if type(spec.timeout_seconds) not in (int, float) or not 0 < spec.timeout_seconds <= 15:
        raise ProviderGateError("invalid timeout")
    if not isinstance(spec.endpoint, str) or not isinstance(spec.expected_hostname, str):
        raise ProviderGateError("invalid endpoint")
    parts = urlsplit(spec.endpoint)
    if (parts.scheme != "https" or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or parts.port not in (None, 443)
            or not parts.hostname or not parts.path.startswith("/")
            or parts.hostname.lower() != spec.expected_hostname.lower()):
        raise ProviderGateError("endpoint must be exact reviewed HTTPS host with no query")
    host = parts.hostname.lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ProviderGateError("private/local endpoint denied")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ProviderGateError("IP literal endpoints denied")
    if any(ord(c) < 33 or ord(c) > 126 for c in spec.endpoint):
        raise ProviderGateError("invalid URL characters")
    return host


def probe_readonly(spec: ProbeSpec, *, secret: str, approved_hostnames: frozenset[str],
                   opener=None) -> dict:
    """Run GET only; network must additionally be restricted by runner egress ACL.

    approved_hostnames must come from independent reviewed configuration.
    An injected opener is for synthetic tests only.
    """
    host = _validate_spec(spec)
    if not isinstance(approved_hostnames, frozenset) or host not in approved_hostnames:
        raise ProviderGateError("host not explicitly approved")
    if not isinstance(secret, str) or not secret.strip() or "\r" in secret or "\n" in secret:
        raise ProviderGateError("missing or unsafe secret")
    header = ("X-API-Key" if spec.auth_scheme == "x-api-key" else "Authorization")
    value = secret if spec.auth_scheme == "x-api-key" else "Bearer " + secret
    request = Request(spec.endpoint, method="GET",
                      headers={header: value, "Accept": "application/json"})
    # Redirects are forbidden: otherwise a remote server could redirect credentials
    # to an attacker-controlled host. Standard urlopen follows redirects.
    if opener is None:
        from urllib.request import build_opener, HTTPSHandler, HTTPRedirectHandler
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
    try:
        with opener.open(request, timeout=spec.timeout_seconds) as response:
            status = response.status
            media_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if status != 200 or media_type not in _ALLOWED_CONTENT_TYPES:
                return {"provider": spec.provider, "connection": "BLOCKED",
                        "forecast": "HOLD", "wager": "NOT APPROVED",
                        "reason": "unexpected status or content type"}
            # Bounded read. Do not return or log provider content.
            payload = response.read(65537)
            if len(payload) > 65536:
                return {"provider": spec.provider, "connection": "BLOCKED",
                        "forecast": "HOLD", "wager": "NOT APPROVED",
                        "reason": "response too large"}
            try:
                decoded = json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                return {"provider": spec.provider, "connection": "BLOCKED",
                        "forecast": "HOLD", "wager": "NOT APPROVED",
                        "reason": "invalid JSON response"}
            if not isinstance(decoded, (dict, list)):
                return {"provider": spec.provider, "connection": "BLOCKED",
                        "forecast": "HOLD", "wager": "NOT APPROVED",
                        "reason": "unexpected JSON shape"}
            return {"provider": spec.provider, "connection": "REACHABLE_ONLY",
                    "forecast": "HOLD", "wager": "NOT APPROVED",
                    "reason": "HTTP 200 JSON; entitlements and identity unverified"}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return {"provider": spec.provider, "connection": "BLOCKED",
                "forecast": "HOLD", "wager": "NOT APPROVED",
                "reason": "probe failed (details withheld)"}
