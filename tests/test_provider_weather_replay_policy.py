"""Offline replay/revocation policy tests."""
import unittest
from extensions.weather_replay_policy import check_attestation_once

VALID = {"signature": "CRYPTOGRAPHICALLY_VERIFIED", "attestation": "SIGNATURE_VALID_ONLY"}


def check(nonce="nonce123456", revoked=frozenset(), used=None, result=VALID):
    return check_attestation_once(nonce=nonce, key_id="key123456",
                                  revoked_key_ids=revoked,
                                  used_nonces=set() if used is None else used,
                                  signature_result=result)


class ReplayPolicyTests(unittest.TestCase):
    def test_first_nonce_test_only(self):
        self.assertEqual(check()["attestation"], "TEST_ONLY_NONCE_ACCEPTED")

    def test_replay_rejected(self):
        used = set()
        self.assertEqual(check(used=used)["attestation"], "TEST_ONLY_NONCE_ACCEPTED")
        self.assertEqual(check(used=used)["attestation"], "BLOCKED")

    def test_revoked_key_rejected(self):
        self.assertEqual(check(revoked=frozenset({"key123456"}))["attestation"], "BLOCKED")

    def test_unverified_signature_rejected(self):
        self.assertEqual(check(result={"signature": "NOT VERIFIED"})["attestation"], "BLOCKED")

    def test_bad_nonce_rejected(self):
        self.assertEqual(check(nonce="https://bad.example")["attestation"], "BLOCKED")

    def test_no_platform_authorization(self):
        r = check()
        self.assertEqual(r["forecast"], "HOLD")
        self.assertEqual(r["wager"], "NOT APPROVED")


if __name__ == "__main__":
    unittest.main()
