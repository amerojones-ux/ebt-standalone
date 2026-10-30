"""Synthetic-only checks for provider gateway. No network or secrets."""
import unittest

from extensions.provider_gateway import (
    PROVIDERS, ProviderGateError, assess_provider, credential_presence,
    inventory, validate_observation,
)

RECORD = {
    "provider": "sportradar", "status": "FOUND",
    "league_id": "NBA", "event_id": "game-001",
    "team_id": "team-01", "player_id": "player-01",
    "source_as_of_utc": "2026-10-30T15:00:00Z",
}


class ProviderGatewayTests(unittest.TestCase):
    def test_all_seven_registered(self):
        self.assertEqual(len(PROVIDERS), 7)

    def test_no_secrets_in_inventory(self):
        env = {v: "TOP_SECRET_123" for v in PROVIDERS.values()}
        data = inventory(env)
        self.assertNotIn("TOP_SECRET_123", str(data))
        self.assertTrue(all(p["credential_present"] for p in data["providers"]))
        self.assertTrue(all(p["status"] == "BLOCKED" for p in data["providers"]))

    def test_empty_secret_is_missing(self):
        self.assertFalse(any(credential_presence({}).values()))
        self.assertFalse(any(credential_presence({k: " " for k in PROVIDERS.values()}).values()))

    def test_credential_does_not_imply_rights(self):
        x = assess_provider("sportradar", environ={"EBT_SPORTRADAR_API_KEY": "fake"})
        self.assertEqual(x.status, "BLOCKED")

    def test_rights_and_feed_both_required(self):
        rights = dict.fromkeys(("model_use", "historical_access", "retention", "derived_analytics"), True)
        env = {"EBT_SPORTRADAR_API_KEY": "fake"}
        self.assertEqual(assess_provider("sportradar", rights=rights, environ=env).status, "BLOCKED")
        claimed = assess_provider("sportradar", rights=rights, feed_verified=True, environ=env)
        self.assertEqual(claimed.status, "BLOCKED")
        self.assertFalse(claimed.rights_verified)
        self.assertFalse(claimed.feed_verified)
        self.assertTrue(claimed.credential_present)

    def test_unhashable_provider_fails_closed(self):
        with self.assertRaises(ProviderGateError):
            assess_provider([], environ={})
        with self.assertRaises(ProviderGateError):
            validate_observation({**RECORD, "provider": []}, as_of_utc="2026-10-30T15:05:00Z")

    def test_malformed_credential_environment_fails_safe(self):
        self.assertFalse(any(credential_presence({"EBT_SPORTRADAR_API_KEY": None}).values()))
        self.assertFalse(any(credential_presence({"EBT_SPORTRADAR_API_KEY": 123}).values()))
        with self.assertRaises(ProviderGateError):
            credential_presence([])

    def test_unhashable_status_fails_closed(self):
        with self.assertRaises(ProviderGateError):
            validate_observation({**RECORD, "status": []}, as_of_utc="2026-10-30T15:05:00Z")

    def test_observation_fingerprint_is_deterministic(self):
        a = validate_observation(RECORD, as_of_utc="2026-10-30T15:05:00Z")
        b = validate_observation(dict(reversed(list(RECORD.items()))),
                                 as_of_utc="2026-10-30T15:05:00Z")
        self.assertEqual(a["source_fingerprint"], b["source_fingerprint"])
        self.assertEqual(a["forecast"], "HOLD")

    def test_stale_fails_closed(self):
        with self.assertRaises(ProviderGateError):
            validate_observation(RECORD, as_of_utc="2026-10-30T17:00:00Z")

    def test_future_fails_closed(self):
        with self.assertRaises(ProviderGateError):
            validate_observation(RECORD, as_of_utc="2026-10-30T14:00:00Z")

    def test_identity_fails_closed(self):
        for key in ("league_id", "event_id", "team_id", "player_id"):
            bad = {**RECORD, key: ""}
            with self.subTest(key=key), self.assertRaises(ProviderGateError):
                validate_observation(bad, as_of_utc="2026-10-30T15:05:00Z")

    def test_bad_source_status_fails_closed(self):
        for status in ("STALE", "CONFLICTING", "BLOCKED", "N_A", "unverified"):
            with self.subTest(status=status), self.assertRaises(ProviderGateError):
                validate_observation({**RECORD, "status": status},
                                     as_of_utc="2026-10-30T15:05:00Z")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ProviderGateError):
            validate_observation({**RECORD, "source_as_of_utc": "2026-10-30T15:00:00"},
                                 as_of_utc="2026-10-30T15:05:00Z")

    def test_negative_age_limit_rejected(self):
        with self.assertRaises(ProviderGateError):
            validate_observation(RECORD, as_of_utc="2026-10-30T15:05:00Z",
                                 max_age_seconds=-1)


if __name__ == "__main__":
    unittest.main()
