"""Canonical entity-resolution tests."""
import unittest

from extensions.entity_resolution import (
    CanonicalEntity, EntityResolutionRegistry, canonicalize_provider_record,
)


class EntityResolutionTests(unittest.TestCase):
    def registry(self):
        r = EntityResolutionRegistry()
        r.register_canonical(CanonicalEntity(
            "player:lebron-james", "player", "LeBron James",
            birth_date="1984-12-30",
            external_ids=(
                ("sportradar_player_id", "abc-123"),
                ("rotowire_player_id", "3125"),
            ),
        ))
        r.register_canonical(CanonicalEntity(
            "team:lal", "team", "Los Angeles Lakers"))
        r.register_canonical(CanonicalEntity(
            "event:2026-01-10-lal-nyk", "event", "LAL @ NYK"))
        return r

    def test_exact_provider_id_resolves(self):
        r = self.registry()
        r.bind_provider_identity(
            entity_type="player", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="100", canonical_id="player:lebron-james")
        result = r.resolve(
            entity_type="player", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="100")
        self.assertEqual(result.status, "RESOLVED")
        self.assertEqual(result.method, "PROVIDER_ID")
        self.assertEqual(result.canonical_id, "player:lebron-james")

    def test_trusted_external_id_can_resolve(self):
        r = self.registry()
        result = r.resolve(
            entity_type="player", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="unknown",
            external_ids={"sportradar_player_id": "abc-123"})
        self.assertEqual(result.status, "RESOLVED")
        self.assertEqual(result.method, "EXTERNAL_ID")

    def test_name_birthdate_only_requires_review(self):
        r = self.registry()
        result = r.resolve(
            entity_type="player", provider_id="API_SPORTS_BASKETBALL",
            provider_entity_id="999",
            display_name="LeBron James", birth_date="1984-12-30")
        self.assertEqual(result.status, "REVIEW")
        self.assertIsNone(result.canonical_id)
        self.assertEqual(result.candidates, ("player:lebron-james",))

    def test_name_alone_never_auto_links(self):
        r = self.registry()
        result = r.resolve(
            entity_type="player", provider_id="API_SPORTS_BASKETBALL",
            provider_entity_id="999", display_name="LeBron James")
        self.assertEqual(result.status, "REVIEW")
        self.assertIsNone(result.canonical_id)

    def test_cross_reference_conflict_fails_closed(self):
        r = self.registry()
        r.register_canonical(CanonicalEntity(
            "player:other", "player", "Other Player",
            external_ids=(("stats_player_id", "777"),),
        ))
        result = r.resolve(
            entity_type="player", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="unknown",
            external_ids={
                "sportradar_player_id": "abc-123",
                "stats_player_id": "777",
            })
        self.assertEqual(result.status, "CONFLICT")
        self.assertIsNone(result.canonical_id)

    def test_record_canonicalization_requires_all_three_entities(self):
        r = self.registry()
        r.bind_provider_identity(
            entity_type="player", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="100", canonical_id="player:lebron-james")
        r.bind_provider_identity(
            entity_type="team", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="20", canonical_id="team:lal")
        r.bind_provider_identity(
            entity_type="event", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="global:300", canonical_id="event:2026-01-10-lal-nyk")

        raw = {
            "event_id": "global:300",
            "team_id": "20",
            "player_id": "100",
            "player_name": "LeBron James",
            "stat": "points",
        }
        out = canonicalize_provider_record(
            raw, provider_id="SPORTSDATAIO_NBA", registry=r)
        self.assertEqual(out["event_id"], "event:2026-01-10-lal-nyk")
        self.assertEqual(out["team_id"], "team:lal")
        self.assertEqual(out["player_id"], "player:lebron-james")
        self.assertEqual(out["provider_event_id"], "global:300")

    def test_missing_event_mapping_holds_even_when_player_matches(self):
        r = self.registry()
        r.bind_provider_identity(
            entity_type="player", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="100", canonical_id="player:lebron-james")
        r.bind_provider_identity(
            entity_type="team", provider_id="SPORTSDATAIO_NBA",
            provider_entity_id="20", canonical_id="team:lal")
        with self.assertRaisesRegex(ValueError, "event:UNRESOLVED"):
            canonicalize_provider_record(
                {"event_id": "global:300", "team_id": "20", "player_id": "100"},
                provider_id="SPORTSDATAIO_NBA", registry=r)


if __name__ == "__main__":
    unittest.main()
