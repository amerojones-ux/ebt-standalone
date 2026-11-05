"""SportsDataIO NBA historical transport tests; no network."""
import json
import unittest
from datetime import datetime, timezone

from sportsdataio_nba_transport import (
    ACCOUNT_REVIEW_APPROVAL,
    REQUEST_APPROVAL,
    SportsDataIONBAHistoricalTransport,
    SportsDataIOTransportError,
)

T0 = datetime(2026, 1, 10, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, payload, url, status=200):
        self.body = json.dumps(payload).encode("utf-8")
        self.url = url
        self.status = status

    def read(self, _limit):
        return self.body


class RecordingOpener:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.payload, request.full_url)


class SportsDataIONBATransportTests(unittest.TestCase):
    def test_exact_approvals_required_before_network(self):
        opener = RecordingOpener([])
        t = SportsDataIONBAHistoricalTransport(
            opener=opener, api_key="test-key")
        with self.assertRaises(PermissionError):
            t.fetch_final_box_scores(
                T0, account_review="NO", confirm=REQUEST_APPROVAL)
        with self.assertRaises(PermissionError):
            t.fetch_final_box_scores(
                T0, account_review=ACCOUNT_REVIEW_APPROVAL, confirm="NO")
        self.assertEqual(opener.requests, [])

    def test_one_request_header_auth_and_date_token(self):
        opener = RecordingOpener([{"Game": {}, "PlayerGames": []}])
        t = SportsDataIONBAHistoricalTransport(
            opener=opener, api_key="test-key")
        result = t.fetch_final_box_scores(
            T0,
            account_review=ACCOUNT_REVIEW_APPROVAL,
            confirm=REQUEST_APPROVAL,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(t.request_count, 1)
        request = opener.requests[0][0]
        self.assertTrue(request.full_url.endswith(
            "/v3/nba/stats/json/BoxScoresFinal/2026-JAN-10"))
        headers = {k.lower(): v for k, v in request.header_items()}
        self.assertEqual(
            headers, {"ocp-apim-subscription-key": "test-key"})

    def test_query_key_is_not_used(self):
        opener = RecordingOpener([])
        t = SportsDataIONBAHistoricalTransport(
            opener=opener, api_key="test-key")
        t.fetch_final_box_scores(
            T0,
            account_review=ACCOUNT_REVIEW_APPROVAL,
            confirm=REQUEST_APPROVAL,
        )
        self.assertNotIn("?", opener.requests[0][0].full_url)

    def test_one_request_budget(self):
        opener = RecordingOpener([])
        t = SportsDataIONBAHistoricalTransport(
            opener=opener, api_key="test-key")
        t.fetch_final_box_scores(
            T0,
            account_review=ACCOUNT_REVIEW_APPROVAL,
            confirm=REQUEST_APPROVAL,
        )
        with self.assertRaises(SportsDataIOTransportError):
            t.fetch_final_box_scores(
                T0,
                account_review=ACCOUNT_REVIEW_APPROVAL,
                confirm=REQUEST_APPROVAL,
            )

    def test_payload_must_be_list_of_objects(self):
        opener = RecordingOpener({"not": "a list"})
        t = SportsDataIONBAHistoricalTransport(
            opener=opener, api_key="test-key")
        with self.assertRaises(SportsDataIOTransportError):
            t.fetch_final_box_scores(
                T0,
                account_review=ACCOUNT_REVIEW_APPROVAL,
                confirm=REQUEST_APPROVAL,
            )

    def test_control_character_in_key_rejected_before_network(self):
        opener = RecordingOpener([])
        t = SportsDataIONBAHistoricalTransport(
            opener=opener, api_key="abc\r\ndef")
        with self.assertRaises(SportsDataIOTransportError):
            t.fetch_final_box_scores(
                T0,
                account_review=ACCOUNT_REVIEW_APPROVAL,
                confirm=REQUEST_APPROVAL,
            )
        self.assertEqual(opener.requests, [])


if __name__ == "__main__":
    unittest.main()
