import unittest
from copy import deepcopy

from ebt_event_gate import EvidenceHold, validate_event_record


def valid():
    return {
        "event_id": "game-1",
        "scheduled_start": "2026-10-30T23:00:00Z",
        "effective_at": "2026-10-29T12:00:00Z",
        "fetched_at": "2026-10-29T12:05:00Z",
        "status": "scheduled",
        "teams": [{"team_id": "team-a"}, {"team_id": "team-b"}],
    }


class EventGateTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_event_record(valid())["team_ids"], ("team-a", "team-b"))

    def test_deleted(self):
        r = valid()
        r["deleted"] = True
        with self.assertRaises(EvidenceHold):
            validate_event_record(r)

    def test_removed_schedule(self):
        r = valid()
        r["deleted_games"] = ["game-1"]
        with self.assertRaises(EvidenceHold):
            validate_event_record(r)

    def test_duplicate_team(self):
        r = valid()
        r["teams"][1]["team_id"] = "team-a"
        with self.assertRaises(EvidenceHold):
            validate_event_record(r)

    def test_future_effective(self):
        r = valid()
        r["effective_at"] = "2026-10-29T12:06:00Z"
        with self.assertRaises(EvidenceHold):
            validate_event_record(r)

    def test_naive_timestamp(self):
        r = valid()
        r["fetched_at"] = "2026-10-29T12:05:00"
        with self.assertRaises(EvidenceHold):
            validate_event_record(r)

    def test_late_scheduled_capture(self):
        r = valid()
        r["fetched_at"] = "2026-10-31T00:00:00Z"
        with self.assertRaises(EvidenceHold):
            validate_event_record(r)

    def test_malformed(self):
        for bad in (None, [], {}, "invalid"):
            with self.subTest(bad=bad), self.assertRaises(EvidenceHold):
                validate_event_record(bad)


if __name__ == "__main__":
    unittest.main()
