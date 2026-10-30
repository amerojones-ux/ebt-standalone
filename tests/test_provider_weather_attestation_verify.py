"""Ed25519 signature-verification regression tests; ephemeral test-only keys."""
import base64
import json
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from extensions.weather_attestation_verify import verify_weather_attestation

COMMIT = "a" * 64
BASE = {
    "schema_version": "1", "repository": "owner/repo",
    "commit_sha": COMMIT, "environment": "staging",
    "decision": "APPROVE", "evidence_digest": "b" * 64,
    "nonce": "nonce123456", "issuer_id": "issuer123456",
    "key_id": "key123456", "issued_at": "2026-10-30T10:00:00Z",
    "expires_at": "2026-10-30T10:30:00Z",
}


def encode(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class WeatherSignatureTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.public = self.private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    def run_check(self, data=BASE, payload=None, signature=None, keys=None, environment="staging"):
        payload = encode(data) if payload is None else payload
        signature = self.private.sign(payload) if signature is None else signature
        return verify_weather_attestation(
            payload=payload, signature_b64=base64.b64encode(signature).decode(),
            key_id="key123456", pinned_public_keys={"key123456": self.public} if keys is None else keys,
            expected_repo="owner/repo", expected_commit=COMMIT,
            expected_environment=environment, now_utc="2026-10-30T10:15:00Z")

    def test_valid_signature_is_not_release_approval(self):
        r = self.run_check()
        self.assertEqual(r["signature"], "CRYPTOGRAPHICALLY_VERIFIED")
        self.assertEqual(r["attestation"], "SIGNATURE_VALID_ONLY")
        self.assertEqual(r["forecast"], "HOLD")

    def test_tampered_payload_fails(self):
        self.assertEqual(self.run_check(signature=b"0" * 64)["attestation"], "BLOCKED")

    def test_wrong_key_fails(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.assertEqual(self.run_check(keys={"key123456": other})["attestation"], "BLOCKED")

    def test_wrong_environment_fails(self):
        self.assertEqual(self.run_check(environment="production")["attestation"], "BLOCKED")

    def test_noncanonical_json_fails(self):
        self.assertEqual(self.run_check(payload=json.dumps(BASE).encode())["attestation"], "BLOCKED")

    def test_unknown_key_fails(self):
        self.assertEqual(self.run_check(keys={})["attestation"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
