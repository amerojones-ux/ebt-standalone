"""Bounded SportsDataIO NBA historical final-box-score transport.

No request occurs without exact account-review and request approval. This module
does not establish entitlement; it only enforces a one-request-per-date plan.
"""
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any, List

HOST = "api.sportsdata.io"
BASE_PATH = "/v3/nba/stats/json/BoxScoresFinal"
MAX_BODY_BYTES = 16 * 1024 * 1024
TIMEOUT_SECONDS = 20

ACCOUNT_REVIEW_APPROVAL = (
    "I_CONFIRM_SPORTSDATAIO_NBA_ACCESS_TIER_FEED_AND_QUOTA_REVIEWED"
)
REQUEST_APPROVAL = (
    "I_APPROVE_ONE_SPORTSDATAIO_NBA_HISTORICAL_REQUEST"
)


class SportsDataIOTransportError(RuntimeError):
    pass


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _default_open(request, timeout):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
    )
    opener.addheaders = []
    return opener.open(request, timeout=timeout)


def _validate_key(key: Any) -> str:
    if not isinstance(key, str) or not key.strip():
        raise SportsDataIOTransportError("SportsDataIO secret unavailable")
    if any(ch in key for ch in "\r\n"):
        raise SportsDataIOTransportError("subscription key contains control characters")
    return key.strip()


def _date_token(target_date: Any) -> str:
    if isinstance(target_date, datetime):
        d = target_date.date()
    elif isinstance(target_date, date):
        d = target_date
    elif isinstance(target_date, str):
        try:
            d = date.fromisoformat(target_date)
        except ValueError as exc:
            raise ValueError("target_date must be YYYY-MM-DD") from exc
    else:
        raise ValueError("target_date must be date/datetime/YYYY-MM-DD")
    return d.strftime("%Y-%b-%d").upper()


class SportsDataIONBAHistoricalTransport:
    def __init__(self, *, opener=None, api_key=None):
        self.opener = _default_open if opener is None else opener
        self._explicit_key = api_key
        self.request_count = 0

    def _key(self):
        return _validate_key(
            self._explicit_key
            if self._explicit_key is not None
            else os.environ.get("EBT_SPORTSDATA_API_KEY")
        )

    def fetch_final_box_scores(
        self, target_date, *, account_review: str, confirm: str
    ) -> List[dict]:
        if account_review != ACCOUNT_REVIEW_APPROVAL:
            raise PermissionError("SportsDataIO NBA account review approval missing")
        if confirm != REQUEST_APPROVAL:
            raise PermissionError("SportsDataIO NBA request approval missing")
        if self.request_count >= 1:
            raise SportsDataIOTransportError("one-request historical budget exceeded")

        token = _date_token(target_date)
        path = f"{BASE_PATH}/{urllib.parse.quote(token, safe='-')}"
        url = f"https://{HOST}{path}"
        request = urllib.request.Request(
            url,
            headers={"Ocp-Apim-Subscription-Key": self._key()},
            method="GET",
        )

        try:
            response = self.opener(request, TIMEOUT_SECONDS)
            self.request_count += 1
            status = getattr(response, "status", None)
            final_url = getattr(response, "url", url)
            parsed = urllib.parse.urlparse(final_url)
            if (
                parsed.scheme != "https"
                or parsed.hostname != HOST
                or parsed.path != path
                or parsed.query
            ):
                raise SportsDataIOTransportError(
                    "redirect, query-key use, or endpoint drift blocked")
            if status != 200:
                raise SportsDataIOTransportError(
                    f"unexpected HTTP status {status}")
            raw = response.read(MAX_BODY_BYTES + 1)
            if len(raw) > MAX_BODY_BYTES:
                raise SportsDataIOTransportError(
                    "response exceeds bounded body limit")
        except urllib.error.HTTPError as exc:
            self.request_count += 1
            raise SportsDataIOTransportError(
                f"HTTP error {exc.code}") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            self.request_count += 1
            raise SportsDataIOTransportError("transport error") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SportsDataIOTransportError("malformed JSON") from exc
        if not isinstance(payload, list):
            raise SportsDataIOTransportError(
                "BoxScoresFinal payload must be a list")
        if any(not isinstance(item, dict) for item in payload):
            raise SportsDataIOTransportError(
                "BoxScoresFinal items must be objects")
        return payload
