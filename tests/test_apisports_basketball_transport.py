"""Bounded API-Sports Basketball transport tests; no network access."""
import io
import json
import unittest
from datetime import datetime, timezone

from apisports_basketball_transport import (
    ACCOUNT_REVIEW_APPROVAL,
    APISportsBasketballHistoricalTransport,
    REQUEST_APPROVAL,
    TransportError,
)

T0 = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, payload, url, status=200):
        self._body = json.dumps(payload).encode("utf-8")
        self.url = url
        self.status = status
        self.headers = {}

    def read(self, _limit):
        return self._body


class SequencedOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        if not self.payloads:
            raise AssertionError("unexpected extra request")
        payload = self.payloads.pop(0)
        return FakeResponse(payload, request.full_url)


def payload(response):
    return {
        "get": "games",
        "parameters": {},
        "errors": [],
        "results": len(response),
        "response": response,
    }


class APISportsBasketballTransportTests(unittest.TestCase):
    def test_no_request_without_exact_approvals(self):
        opener = SequencedOpener([])
        transport = APISportsBasketballHistoricalTransport(
            opener=opener, api_key="test-key")
        with self.assertRaises(PermissionError):
            transport.fetch_nba_date(
                T0, account_review="NO", confirm=REQUEST_APPROVAL)
        with self.assertRaises(PermissionError):
            transport.fetch_nba_date(
                T0, account_review=ACCOUNT_REVIEW_APPROVAL, confirm="NO")
        self.assertEqual(opener.requests, [])
        self.assertEqual(transport.request_count, 0)

    def test_one_date_uses_two_requests_and_batches_game_ids(self):
        games = payload([
            {"id": 1001, "date": T0.isoformat(), "status": {"short": "FT"}},
            {"id": 1002, "date": T0.isoformat(), "status": {"short": "AOT"}},
        ])
        stats = payload([
            {"game": {"id": 1001}, "team": {"id": 1}, "player": {"id": 10}},
        ])
        opener = SequencedOpener([games, stats])
        transport = APISportsBasketballHistoricalTransport(
            opener=opener, api_key="test-key")
        result = transport.fetch_nba_date(
            T0,
            account_review=ACCOUNT_REVIEW_APPROVAL,
            confirm=REQUEST_APPROVAL,
        )
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(len(opener.requests), 2)
        first_url = opener.requests[0][0].full_url
        second_url = opener.requests[1][0].full_url
        self.assertIn("/games?", first_url)
        self.assertIn("league=12", first_url)
        self.assertIn("timezone=UTC", first_url)
        self.assertIn("/games/statistics/players?", second_url)
        self.assertIn("ids=1001-1002", second_url)
        first_headers = dict(opener.requests[0][0].header_items())
        self.assertEqual(
            {k.lower(): v for k, v in first_headers.items()},
            {"x-apisports-key": "test-key"},
        )

    def test_zero_games_uses_only_schedule_request(self):
        opener = SequencedOpener([payload([])])
        transport = APISportsBasketballHistoricalTransport(
            opener=opener, api_key="test-key")
        result = transport.fetch_nba_date(
            "2026-01-10",
            account_review=ACCOUNT_REVIEW_APPROVAL,
            confirm=REQUEST_APPROVAL,
        )
        self.assertEqual(result["request_count"], 1)
        self.assertIsNone(result["player_stats_payload"])

    def test_more_than_twenty_games_fails_before_stats_request(self):
        opener = SequencedOpener([
            payload([{"id": x} for x in range(1, 22)])
        ])
        transport = APISportsBasketballHistoricalTransport(
            opener=opener, api_key="test-key")
        with self.assertRaises(TransportError):
            transport.fetch_nba_date(
                T0,
                account_review=ACCOUNT_REVIEW_APPROVAL,
                confirm=REQUEST_APPROVAL,
            )
        self.assertEqual(len(opener.requests), 1)

    def test_provider_result_count_mismatch_fails_closed(self):
        bad = {
            "get": "games", "parameters": {}, "errors": [],
            "results": 2, "response": [{"id": 1}],
        }
        opener = SequencedOpener([bad])
        transport = APISportsBasketballHistoricalTransport(
            opener=opener, api_key="test-key")
        with self.assertRaises(TransportError):
            transport.fetch_nba_date(
                T0,
                account_review=ACCOUNT_REVIEW_APPROVAL,
                confirm=REQUEST_APPROVAL,
            )

    def test_request_budget_cannot_exceed_two(self):
        opener = SequencedOpener([payload([]), payload([]), payload([])])
        transport = APISportsBasketballHistoricalTransport(
            opener=opener, api_key="test-key")
        transport._get("/games", {"date": "2026-01-10", "league": 12})
        transport._get("/games", {"date": "2026-01-11", "league": 12})
        with self.assertRaises(TransportError):
            transport._get("/games", {"date": "2026-01-12", "league": 12})


if __name__ == "__main__":
    unittest.main()
