import io
import json
import stat
import unittest
import zipfile

from apisports_status_receipt import build_receipt as build_apisports
from theoddsapi_probe_receipt import build_receipt as build_odds
from weatherapi_probe_receipt import build_receipt as build_weather
from provider_artifact_receipt_ingest import ingest_artifact_bytes

COMMIT="a"*40
RUN="123456"

def zip_one(name,payload,*,external_attr=None,flag_bits=0):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        info=zipfile.ZipInfo(name)
        info.compress_type=zipfile.ZIP_DEFLATED
        info.flag_bits=flag_bits
        if external_attr is not None:
            info.external_attr=external_attr
        zf.writestr(info,payload)
    return out.getvalue()

def weather_receipt():
    return build_weather(
        {"status":"PASS","category":"authenticated_schema_fresh"},
        "2026-11-02T20:00:00+00:00",COMMIT,RUN
    )

def odds_receipt():
    return build_odds(
        {"status":"PASS","category":"authenticated_zero_credit_sports_schema"},
        "2026-11-02T20:00:00+00:00",COMMIT,RUN
    )

def api_receipt():
    return build_apisports(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:00:00+00:00",COMMIT,RUN
    )

class ProviderArtifactReceiptIngestTests(unittest.TestCase):
    def test_weather_artifact_ingests_pending_attestation(self):
        raw=(json.dumps(weather_receipt(),sort_keys=True)+"\n").encode()
        result=ingest_artifact_bytes(
            zip_one("weatherapi_probe_receipt.json",raw),
            provider="WeatherAPI",expected_run_id=RUN,expected_commit=COMMIT,
        )
        self.assertEqual(result["ingestion_status"],"PENDING_ATTESTATION")
        self.assertEqual(result["candidate"]["provider"],"WeatherAPI")
        self.assertEqual(result["candidate"]["artifact_sha256"],result["receipt_file_sha256"])
        self.assertEqual(result["candidate"]["receipt_sha256"],result["receipt_internal_sha256"])
        self.assertNotEqual(result["receipt_file_sha256"],result["receipt_internal_sha256"])
        self.assertFalse(result["ledger_mutation_permitted"])
        self.assertFalse(result["readiness_mutation_permitted"])
        self.assertFalse(result["forecast_activation_permitted"])

    def test_all_supported_provider_filenames(self):
        cases=[
            ("The Odds API","theoddsapi_probe_receipt.json",odds_receipt()),
            ("API-Sports","apisports_status_receipt.json",api_receipt()),
        ]
        for provider,name,receipt in cases:
            with self.subTest(provider=provider,expected_run_id=RUN,expected_commit=COMMIT):
                raw=json.dumps(receipt).encode()
                r=ingest_artifact_bytes(zip_one(name,raw),provider=provider,expected_run_id=RUN,expected_commit=COMMIT)
                self.assertEqual(r["candidate"]["provider"],provider)

    def test_extra_file_rejected(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w") as zf:
            zf.writestr("weatherapi_probe_receipt.json",json.dumps(weather_receipt()))
            zf.writestr("extra.txt","x")
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(out.getvalue(),provider="WeatherAPI",expected_run_id=RUN,expected_commit=COMMIT)

    def test_wrong_or_nested_filename_rejected(self):
        raw=json.dumps(weather_receipt()).encode()
        for name in ("other.json","nested/weatherapi_probe_receipt.json","../weatherapi_probe_receipt.json"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    ingest_artifact_bytes(zip_one(name,raw),provider="WeatherAPI",expected_run_id=RUN,expected_commit=COMMIT)

    def test_symlink_member_rejected(self):
        raw=json.dumps(weather_receipt()).encode()
        symlink_mode=(stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(
                zip_one("weatherapi_probe_receipt.json",raw,external_attr=symlink_mode),
                provider="WeatherAPI",expected_run_id=RUN,expected_commit=COMMIT,
            )

    def test_invalid_json_rejected(self):
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(
                zip_one("weatherapi_probe_receipt.json",b"{"),
                provider="WeatherAPI",expected_run_id=RUN,expected_commit=COMMIT,
            )

    def test_hold_receipt_rejected_from_review_candidate(self):
        receipt=build_weather(
            {"status":"HOLD","category":"transport_error"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(
                zip_one("weatherapi_probe_receipt.json",json.dumps(receipt).encode()),
                provider="WeatherAPI",expected_run_id=RUN,expected_commit=COMMIT,
            )

    def test_trusted_run_id_mismatch_rejected(self):
        raw=json.dumps(weather_receipt()).encode()
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(
                zip_one("weatherapi_probe_receipt.json",raw),
                provider="WeatherAPI",expected_run_id="999999",expected_commit=COMMIT,
            )

    def test_trusted_commit_mismatch_rejected(self):
        raw=json.dumps(weather_receipt()).encode()
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(
                zip_one("weatherapi_probe_receipt.json",raw),
                provider="WeatherAPI",expected_run_id=RUN,expected_commit="b"*40,
            )

    def test_provider_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(
                zip_one("weatherapi_probe_receipt.json",json.dumps(weather_receipt()).encode()),
                provider="API-Sports",expected_run_id=RUN,expected_commit=COMMIT,
            )

    def test_oversized_zip_rejected(self):
        with self.assertRaises(ValueError):
            ingest_artifact_bytes(b"x"*(1024*1024+1),provider="WeatherAPI",expected_run_id=RUN,expected_commit=COMMIT)

if __name__=="__main__":
    unittest.main()
