"""Strict offline endpoint policy checks; no network requests or secrets.

Host and path must match an explicit allowlist. This does not establish TLS
peer authentication; that requires the actual HTTPS transport and trusted CA.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit
import ipaddress

@dataclass(frozen=True)
class EndpointPolicy:
    provider: str
    allowed_host: str
    allowed_path_prefix: str

def verify_url(policy: EndpointPolicy, url: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme != "https" or not host or not policy.allowed_host:
            return ("FAIL", "HTTPS_REQUIRED")
        if parsed.username is not None or parsed.password is not None:
            return ("FAIL", "URL_CREDENTIALS_FORBIDDEN")
        if parsed.port not in (None, 443):
            return ("FAIL", "NONSTANDARD_PORT")
        if host.lower().rstrip(".") != policy.allowed_host.lower().rstrip("."):
            return ("FAIL", "HOST_NOT_ALLOWLISTED")
        if host == "localhost" or host.endswith(".local"):
            return ("FAIL", "LOCAL_HOST_FORBIDDEN")
        try:
            ipaddress.ip_address(host)
            return ("FAIL", "IP_LITERAL_FORBIDDEN")
        except ValueError:
            pass
        prefix = policy.allowed_path_prefix
        if not prefix.startswith("/") or ".." in parsed.path.split("/"):
            return ("FAIL", "PATH_POLICY_INVALID")
        if not (parsed.path == prefix.rstrip("/") or parsed.path.startswith(prefix.rstrip("/") + "/")):
            return ("FAIL", "PATH_NOT_ALLOWLISTED")
        if parsed.fragment:
            return ("FAIL", "FRAGMENT_FORBIDDEN")
        return ("PASS", "URL_POLICY_ONLY")
    except (ValueError, TypeError, AttributeError):
        return ("FAIL", "URL_INVALID")
