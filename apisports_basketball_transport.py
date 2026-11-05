"""Bounded API-Sports Basketball historical transport.

This module is intentionally separate from mapping/model code. It performs at
most two requests for one NBA date: games + batched player statistics (<=20 IDs).
No request occurs without exact account-review and request approvals.
"""
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional

HOST = "v1.basketball.api-sports.io"
BASE_URL = f"https://{HOST}"
NBA_LEAGUE_ID = 12
MAX_BODY_BYTES = 8 * 1024 * 1024
TIMEOUT_SECONDS = 15

ACCOUNT_REVIEW_APPROVAL = (
    "I_CONFIRM_APISPORTS_BASKETBALL_ACCESS_TIER_AND_QUOTA_REVIEWED"
)
REQUEST_APPROVAL = (
    "I_APPROVE_TWO_APISPORTS_BASKETBALL_HISTORICAL_REQUESTS"
)
ALLOWED_PATHS = {"/games", "/games/statistics/players"}


class TransportError(RuntimeError):
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
        raise TransportError("API-Sports Basketball secret unavailable")
    if any(ch in key for ch in "\r\n"):
        raise TransportError("API key contains invalid control characters")
    return key.strip()


def _date_text(target_date: Any) -> str:
    if isinstance(target_date, datetime):
        return target_date.date().isoformat()
    if isinstance(target_date, date):
        return target_date.isoformat()
    if isinstance(target_date, str):
        try:
            return date.fromisoformat(target_date).isoformat()
        except ValueError as exc:
            raise ValueError("target_date must be YYYY-MM-DD") from exc
    raise ValueError("target_date must be date/datetime/YYYY-MM-DD")


class APISportsBasketballHistoricalTransport:
    def __init__(self, *, opener=None, api_key=None):
        self.opener = _default_open if opener is None else opener
        self._explicit_key = api_key
        self.request_count = 0

    def _key(self):
        return _validate_key(
            self._explicit_key
            if self._explicit_key is not None
            else os.environ.get("EBT_APISPORTS_API_KEY")
        )

    @staticmethod
    def _url(path: str, params: Mapping[str, Any]) -> str:
        if path not in ALLOWED_PATHS:
            raise TransportError("endpoint not allowlisted")
        query = urllib.parse.urlencode(
            [(str(k), str(v)) for k, v in sorted(params.items())],
            doseq=False,
            safe="-",
        )
        return f"{BASE_URL}{path}?{query}"

    def _get(self, path: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        if self.request_count >= 2:
            raise TransportError("two-request historical budget exceeded")
        url = self._url(path, params)
        request = urllib.request.Request(
            url,
            headers={"x-apisports-key": self._key()},
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
            ):
                raise TransportError("redirect or endpoint drift blocked")
            if status != 200:
                raise TransportError(f"unexpected HTTP status {status}")
            raw = response.read(MAX_BODY_BYTES + 1)
            if len(raw) > MAX_BODY_BYTES:
                raise TransportError("response exceeds bounded body limit")
        except urllib.error.HTTPError as exc:
            self.request_count += 1
            raise TransportError(f"HTTP error {exc.code}") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            self.request_count += 1
            raise TransportError("transport error") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TransportError("malformed JSON") from exc
        if not isinstance(payload, dict):
            raise TransportError("provider payload must be an object")
        for field in ("get", "parameters", "errors", "results", "response"):
            if field not in payload:
                raise TransportError(f"provider payload missing {field}")
        errors = payload["errors"]
        if errors not in ({}, []):
            raise TransportError("provider returned API errors")
        if type(payload["results"]) is not int or payload["results"] < 0:
            raise TransportError("provider results count invalid")
        if not isinstance(payload["response"], list):
            raise TransportError("provider response must be a list")
        if payload["results"] != len(payload["response"]):
            raise TransportError("provider results count mismatch")
        return payload

    def fetch_nba_date(
        self,
        target_date,
        *,
        account_review: str,
        confirm: str,
        timezone_name: str = "UTC",
    ) -> Dict[str, Any]:
        """Retrieve one NBA date using exactly two requests when games exist."""
        if account_review != ACCOUNT_REVIEW_APPROVAL:
            raise PermissionError("API-Sports Basketball account review approval missing")
        if confirm != REQUEST_APPROVAL:
            raise PermissionError("API-Sports Basketball request approval missing")
        if not isinstance(timezone_name, str) or not timezone_name.strip():
            raise ValueError("timezone_name required")

        date_text = _date_text(target_date)
        games = self._get(
            "/games",
            {"date": date_text, "league": NBA_LEAGUE_ID, "timezone": timezone_name},
        )
        game_ids = []
        for game in games["response"]:
            if not isinstance(game, dict) or type(game.get("id")) is not int:
                raise TransportError("game identity schema invalid")
            game_ids.append(game["id"])
        if not game_ids:
            return {
                "games_payload": games,
                "player_stats_payload": None,
                "request_count": self.request_count,
            }
        if len(game_ids) > 20:
            raise TransportError("NBA date exceeds documented 20-game batch limit")
        stats = self._get(
            "/games/statistics/players",
            {"ids": "-".join(str(x) for x in game_ids)},
        )
        return {
            "games_payload": games,
            "player_stats_payload": stats,
            "request_count": self.request_count,
        }
