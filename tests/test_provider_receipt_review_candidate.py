import unittest

from apisports_status_receipt import build_receipt as build_apisports
from theoddsapi_probe_receipt import build_receipt as build_odds
from weatherapi_probe_receipt import build_receipt as build_weather
from provider_receipt_review_candidate import build_review_candidate, bind_attestation_verification
from provider_live_request_plan import request_plan_sha256

COMMIT="a"*40
INTENT_SHA="3"*64
RUN="123456"
ARTIFACT="d"*64
MARKER="e"*64
REQUEST_PLAN=request_plan_sha256("WeatherAPI")
REPO="amerojones-ux/ebt-standalone"
ATTESTATION_ID="attestation-123"
ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+ATTESTATION_ID
SIGNER=".github/workflows/weatherapi-live-probe.yml"

EXECUTION_KWARGS={
    "execution_intent_sha256":"3"*64,
    "execution_intent_file_sha256":"4"*64,
    "execution_intent_marker_sha256":"5"*64,
    "execution_intent_bundle_sha256":"6"*64,
    "execution_intent_attestation_id":"intent-attestation-123",
    "execution_intent_attestation_url":
        "https://github.com/"+REPO+"/attestations/intent-attestation-123",
    "execution_actor":"amerojones-ux",
    "execution_actor_id":"262097315",
    "execution_max_requests":1,
}
_raw_build_weather=build_weather
_raw_build_odds=build_odds
_raw_build_apisports=build_apisports

def build_weather(*args,**kwargs):
    kwargs.setdefault("execution_intent_sha256",INTENT_SHA)
    return _raw_build_weather(*args,**kwargs)

def build_odds(*args,**kwargs):
    kwargs.setdefault("execution_intent_sha256",INTENT_SHA)
    return _raw_build_odds(*args,**kwargs)

def build_apisports(*args,**kwargs):
    kwargs.setdefault("execution_intent_sha256",INTENT_SHA)
    return _raw_build_apisports(*args,**kwargs)

class ProviderReceiptReviewCandidateTests(unittest.TestCase):
    def test_weather_pass_becomes_review_only_candidate(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        c=build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)
        self.assertEqual(c["provider"],"WeatherAPI")
        self.assertEqual(c["subject"],"WeatherAPI")
        self.assertEqual(c["claim"],"live_auth_verified")
        self.assertEqual(c["candidate_status"],"REVIEW_ONLY_PENDING_ATTESTATION")
        self.assertIs(c["attestation_verified"],False)
        self.assertIsNone(c["attestation_marker_sha256"])
        self.assertIsNone(c["request_plan_sha256"])
        self.assertIsNone(c["source_repository"])
        self.assertIsNone(c["attestation_id"])
        self.assertIsNone(c["attestation_url"])
        self.assertIsNone(c["signer_workflow"])
        self.assertIs(c["execution_intent_verified"],False)
        self.assertEqual(c["execution_intent_sha256"],INTENT_SHA)
        self.assertIsNone(c["execution_actor"])
        self.assertIsNone(c["execution_max_requests"])
        self.assertIs(c["github_metadata_match"],True)
        self.assertFalse(c["readiness_mutation_permitted"])
        self.assertFalse(c["forecast_activation_permitted"])
        self.assertEqual(len(c["candidate_sha256"]),64)

    def test_verified_attestation_promotes_candidate_to_review_only(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        pending=build_review_candidate(
            r,artifact_sha256=ARTIFACT,
            expected_run_id=RUN,expected_commit=COMMIT
        )
        final=bind_attestation_verification(
            pending,
            marker_sha256=MARKER,
            request_plan_sha256=REQUEST_PLAN,
            source_repository=REPO,
            attestation_id=ATTESTATION_ID,
            attestation_url=ATTESTATION_URL,
            signer_workflow=SIGNER,
            **EXECUTION_KWARGS,
        )
        self.assertEqual(final["candidate_status"],"REVIEW_ONLY")
        self.assertIs(final["attestation_verified"],True)
        self.assertEqual(final["attestation_marker_sha256"],MARKER)
        self.assertEqual(final["request_plan_sha256"],REQUEST_PLAN)
        self.assertEqual(final["source_repository"],REPO)
        self.assertEqual(final["attestation_id"],ATTESTATION_ID)
        self.assertEqual(final["attestation_url"],ATTESTATION_URL)
        self.assertEqual(final["signer_workflow"],SIGNER)
        self.assertIs(final["execution_intent_verified"],True)
        self.assertEqual(
            final["execution_intent_sha256"],
            EXECUTION_KWARGS["execution_intent_sha256"],
        )
        self.assertEqual(
            final["execution_actor"],EXECUTION_KWARGS["execution_actor"]
        )
        self.assertEqual(final["execution_max_requests"],1)

    def test_receipt_intent_checksum_mismatch_rejected_during_bind(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        pending=build_review_candidate(
            r,artifact_sha256=ARTIFACT,
            expected_run_id=RUN,expected_commit=COMMIT
        )
        bad=dict(EXECUTION_KWARGS)
        bad["execution_intent_sha256"]="7"*64
        with self.assertRaises(ValueError):
            bind_attestation_verification(
                pending,
                marker_sha256=MARKER,
                request_plan_sha256=REQUEST_PLAN,
                source_repository=REPO,
                attestation_id=ATTESTATION_ID,
                attestation_url=ATTESTATION_URL,
                signer_workflow=SIGNER,
                **bad,
            )

    def test_wrong_source_repository_rejected_during_attestation_bind(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        pending=build_review_candidate(
            r,artifact_sha256=ARTIFACT,
            expected_run_id=RUN,expected_commit=COMMIT
        )
        with self.assertRaises(ValueError):
            bind_attestation_verification(
                pending,
                marker_sha256=MARKER,
            request_plan_sha256=REQUEST_PLAN,
                source_repository="other/repo",
                attestation_id=ATTESTATION_ID,
                attestation_url=ATTESTATION_URL,
                signer_workflow=SIGNER,
                **EXECUTION_KWARGS,
            )

    def test_wrong_signer_rejected_during_attestation_bind(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        pending=build_review_candidate(
            r,artifact_sha256=ARTIFACT,
            expected_run_id=RUN,expected_commit=COMMIT
        )
        with self.assertRaises(ValueError):
            bind_attestation_verification(
                pending,
                marker_sha256=MARKER,
            request_plan_sha256=REQUEST_PLAN,
                source_repository=REPO,
                attestation_id=ATTESTATION_ID,
                attestation_url=ATTESTATION_URL,
                signer_workflow=".github/workflows/apisports-status-probe.yml",
                **EXECUTION_KWARGS,
            )

    def test_odds_pass_becomes_review_only_candidate(self):
        r=build_odds(
            {"status":"PASS","category":"authenticated_zero_credit_sports_schema"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        self.assertEqual(build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)["provider"],"The Odds API")

    def test_apisports_pass_becomes_review_only_candidate(self):
        r=build_apisports(
            {"status":"PASS","category":"authenticated_status_schema"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        self.assertEqual(build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)["provider"],"API-Sports")

    def test_hold_receipt_rejected(self):
        r=build_weather(
            {"status":"HOLD","category":"transport_error"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        with self.assertRaises(ValueError):
            build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)

    def test_tampered_receipt_rejected(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        r["status"]="HOLD"
        with self.assertRaises(ValueError):
            build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)

    def test_missing_commit_rejected(self):
        r=build_odds(
            {"status":"PASS","category":"authenticated_zero_credit_sports_schema"},
            "2026-11-02T20:00:00+00:00","",RUN
        )
        with self.assertRaises(ValueError):
            build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)

    def test_missing_run_id_rejected(self):
        r=build_apisports(
            {"status":"PASS","category":"authenticated_status_schema"},
            "2026-11-02T20:00:00+00:00",COMMIT,""
        )
        with self.assertRaises(ValueError):
            build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)

    def test_trusted_run_id_mismatch_rejected(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        with self.assertRaises(ValueError):
            build_review_candidate(
                r,artifact_sha256=ARTIFACT,
                expected_run_id="999999",expected_commit=COMMIT,
            )

    def test_trusted_commit_mismatch_rejected(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        with self.assertRaises(ValueError):
            build_review_candidate(
                r,artifact_sha256=ARTIFACT,
                expected_run_id=RUN,expected_commit="b"*40,
            )

    def test_candidate_contains_only_sanitized_provenance(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        c=build_review_candidate(r,artifact_sha256=ARTIFACT,expected_run_id=RUN,expected_commit=COMMIT)
        rendered=repr(c).lower()
        self.assertNotIn("api_key",rendered)
        self.assertNotIn("headers",rendered)
        self.assertNotIn("response",rendered)
        self.assertNotIn("quota",rendered)

if __name__=="__main__":
    unittest.main()
