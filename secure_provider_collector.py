"""Bounded read-only HTTPS collector for explicitly approved endpoints.

Never pass credentials in URL or logs. Redirects disabled. Uses OS TLS trust.
No requests occur on import. Operator must explicitly call collect().
"""
from dataclasses import dataclass
from urllib.request import Request, build_opener, HTTPSHandler, ProxyHandler
from urllib.error import HTTPError, URLError
import ssl
from provider_endpoint_policy import EndpointPolicy, verify_url

@dataclass(frozen=True)
class CollectorConfig:
    timeout_seconds: float = 5.0
    max_body_bytes: int = 262144

@dataclass(frozen=True)
class CollectorResult:
    status: str
    http_status: int | None
    body: bytes | None
    reason: str

from urllib.request import HTTPRedirectHandler
class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def collect(policy: EndpointPolicy, url: str, *, config: CollectorConfig = CollectorConfig(),
            headers: dict[str,str] | None = None) -> CollectorResult:
    verdict, reason = verify_url(policy, url)
    if verdict != "PASS":
        return CollectorResult("FAIL", None, None, reason)
    if config.timeout_seconds <= 0 or config.timeout_seconds > 15 or config.max_body_bytes < 1 or config.max_body_bytes > 1048576:
        return CollectorResult("FAIL", None, None, "UNSAFE_LIMITS")
    if headers:
        for key, value in headers.items():
            if not isinstance(key, str) or not isinstance(value, str) or not key.isascii() or not key.replace("-", "").isalnum() or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
                return CollectorResult("FAIL", None, None, "INVALID_HEADER")
            if key.lower() not in ("accept", "user-agent", "authorization", "x-api-key", "x-rapidapi-key", "x-rapidapi-host"):
                return CollectorResult("FAIL", None, None, "HEADER_NOT_ALLOWLISTED")
    try:
        request = Request(url, headers=headers or {}, method="GET")
        opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), RejectRedirect())
        with opener.open(request, timeout=config.timeout_seconds) as response:
            status = response.status
            if status != 200:
                return CollectorResult("HOLD", status, None, "HTTP_UNEXPECTED")
            data = response.read(config.max_body_bytes + 1)
            if len(data) > config.max_body_bytes:
                return CollectorResult("HOLD", status, None, "BODY_TOO_LARGE")
            return CollectorResult("CAPTURED_UNVERIFIED", status, data, "AWAITING_SCHEMA_AND_PROVENANCE")
    except HTTPError as exc:
        return CollectorResult("HOLD", exc.code, None, "HTTP_ERROR")
    except (URLError, TimeoutError, OSError, ValueError):
        return CollectorResult("HOLD", None, None, "TRANSPORT_ERROR")
