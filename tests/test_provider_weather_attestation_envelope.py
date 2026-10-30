"""Synthetic tests for signed-attestation envelope preflight."""
import unittest
from extensions.weather_attestation_envelope import inspect_attestation_envelope as inspect

COMMIT = "a" * 64
BASE = {
    "schema_version": "1", "repository": "owner/repo",
    "commit_sha": COMMIT, "environment": "staging",
    "decision": "APPROVE", "evidence_digest": "b" * 64,
    "nonce": "nonce123456", "issuer_id": "issuer123456",
    "key_id": "key123456", "issued_at": "2026-10-30T10:00:00Z",
    "expires_at": "2026-10-30T10:30:00Z",
}


def run(record):
    return inspect(record, expected_repo="owner/repo", expected_commit=COMMIT,
                   expected_environment="staging", now_utc="2026-10-30T10:15:00Z")


class AttestationEnvelopeTests(unittest.TestCase):
    def test_valid_structure_not_signature(self):
        r = run(BASE)
        self.assertEqual(r["envelope"], "STRUCTURALLY_VALID_ONLY")
        self.assertEqual(r["signature"], "NOT VERIFIED")
        self.assertEqual(r["forecast"], "HOLD")

    def test_wrong_commit_blocked(self):
        self.assertEqual(run({**BASE, "commit_sha": "c" * 64})["envelope"], "BLOCKED")

    def test_wrong_environment_blocked(self):
        self.assertEqual(run({**BASE, "environment": "production"})["envelope"], "BLOCKED")

    def test_expired_blocked(self):
        self.assertEqual(run({**BASE, "expires_at": "2026-10-30T10:10:00Z"})["envelope"], "BLOCKED")

    def test_future_issued_blocked(self):
        self.assertEqual(run({**BASE, "issued_at": "2026-10-30T10:20:00Z"})["envelope"], "BLOCKED")

    def test_excessive_lifetime_blocked(self):
        self.assertEqual(run({**BASE, "expires_at": "2026-10-31T10:30:00Z"})["envelope"], "BLOCKED")

    def test_malformed_nonce_blocked(self):
        self.assertEqual(run({**BASE, "nonce": "https://secret.example/?key=bad"})["envelope"], "BLOCKED")

    def test_no_secret_echo(self):
        self.assertNotIn("SECRET", str(run({**BASE, "issuer_id": "SECRET=KEY"})))


if __name__ == "__main__":
    unittest.main()
