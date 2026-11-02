"""Strict offline endpoint allowlisting. No network calls or credentials."""
from dataclasses import dataclass
from urllib.parse import urlsplit, unquote
import ipaddress

@dataclass(frozen=True)
class EndpointPolicy:
    provider: str
    allowed_host: str
    allowed_path_prefix: str

def verify_url(policy: EndpointPolicy, url: str) -> tuple[str, str]:
    try:
        if not isinstance(url, str) or any(ord(ch) < 33 or ord(ch) == 127 for ch in url):
            return ("FAIL", "URL_INVALID")
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
        decoded = unquote(parsed.path)
        if (not prefix.startswith("/") or not decoded.startswith("/") or
            any(part in (".", "..") for part in decoded.split("/")) or
            "\\" in decoded or "%" in decoded):
            return ("FAIL", "PATH_POLICY_INVALID")
        normalized_prefix = prefix.rstrip("/")
        if not (decoded == normalized_prefix or decoded.startswith(normalized_prefix + "/")):
            return ("FAIL", "PATH_NOT_ALLOWLISTED")
        if parsed.query:
            return ("FAIL", "QUERY_STRING_REQUIRES_PROVIDER_CONTRACT")
        if parsed.fragment:
            return ("FAIL", "FRAGMENT_FORBIDDEN")
        return ("PASS", "URL_POLICY_ONLY")
    except (ValueError, TypeError, AttributeError):
        return ("FAIL", "URL_INVALID")
