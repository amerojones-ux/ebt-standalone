import copy
import json
import unittest
from unittest.mock import patch

from provider_live_auth_promotion_apply import build_live_auth_promotion_apply

def readiness():
    from tests.provider_test_fixtures import readiness as synthetic_fixture
    return synthetic_fixture()

def ledger():
    from tests.provider_test_fixtures import ledger as synthetic_fixture
    return synthetic_fixture()

def fresh_preview():
    r=readiness()
    l=ledger()
    for entry in r["providers"]:
        if entry["name"]=="WeatherAPI":
            entry["live_auth_verified"]=True
    for entry in l["providers"]:
        if entry["name"]=="WeatherAPI":
            entry["evidence"]["live_auth_verified"]={"status":"VERIFIED"}
    return {
        "preview_status":"VALID_LIVE_AUTH_PROMOTION_PREVIEW",
        "provider":"WeatherAPI",
        "claim":"live_auth_verified",
        "decision_sha256":"1"*64,
        "global_provider_gate":"SAFE_HOLD",
        "ledger_write_permitted":False,
        "readiness_write_permitted":False,
        "forecast_activation_permitted":False,
        "preview_ledger":l,
        "preview_readiness":r,
        "preview_sha256":"2"*64,
    }

def package(pv=None):
    if pv is None:
        pv=fresh_preview()
    return {
        "package_status":"VERIFIED_LIVE_AUTH_PROMOTION_PREVIEW_PACKAGE",
        "provider":"WeatherAPI",
        "claim":"live_auth_verified",
        "source_probe_run_id":"41717111914",
        "review_run_id":"41719029128",
        "promotion_preview_run_id":"41719559583",
        "promotion_preview_commit":"a"*40,
        "preview_sha256":pv["preview_sha256"],
        "attested_review_decision":{"decision":"APPROVE"},
        "signed_preview":pv,
        "attestation_marker":{},
    }

class LiveAuthPromotionApplyTests(unittest.TestCase):
    @patch("provider_live_auth_promotion_apply.evidence_supports_readiness",return_value=[])
    @patch("provider_live_auth_promotion_apply.validate_config",return_value=[])
    @patch("provider_live_auth_promotion_apply.status",return_value="SAFE_HOLD")
    def test_valid_apply_changes_only_live_auth(self,_status,_validate,_evidence):
        pv=fresh_preview()
        with patch("provider_live_auth_promotion_apply.build_live_auth_promotion_preview",return_value=pv):
            result=build_live_auth_promotion_apply(
                readiness(),ledger(),package(pv),
                trusted_now="2026-11-03T21:13:00+00:00",
            )
        self.assertEqual(result["apply_status"],"VALID_LIVE_AUTH_PROMOTION_APPLY")
        self.assertEqual(result["global_provider_gate"],"SAFE_HOLD")
        self.assertFalse(result["forecast_enabled"])
        self.assertFalse(result["network_autorun_enabled"])
        self.assertFalse(result["forecast_activation_permitted"])
        self.assertFalse(result["provider_network_request_permitted"])
        target=next(
            x for x in result["updated_readiness"]["providers"]
            if x["name"]=="WeatherAPI"
        )
        self.assertTrue(target["live_auth_verified"])

    @patch("provider_live_auth_promotion_apply.evidence_supports_readiness",return_value=[])
    @patch("provider_live_auth_promotion_apply.validate_config",return_value=[])
    @patch("provider_live_auth_promotion_apply.status",return_value="SAFE_HOLD")
    def test_signed_preview_drift_rejected(self,_status,_validate,_evidence):
        signed=fresh_preview()
        rebuilt=copy.deepcopy(signed)
        rebuilt["preview_sha256"]="3"*64
        with patch("provider_live_auth_promotion_apply.build_live_auth_promotion_preview",return_value=rebuilt):
            with self.assertRaises(ValueError):
                build_live_auth_promotion_apply(
                    readiness(),ledger(),package(signed),
                    trusted_now="2026-11-03T21:13:00+00:00",
                )

    @patch("provider_live_auth_promotion_apply.evidence_supports_readiness",return_value=[])
    @patch("provider_live_auth_promotion_apply.validate_config",return_value=[])
    @patch("provider_live_auth_promotion_apply.status",return_value="ELIGIBLE_FOR_MANUAL_ACTIVATION_REVIEW")
    def test_apply_cannot_cross_safe_hold(self,_status,_validate,_evidence):
        pv=fresh_preview()
        with patch("provider_live_auth_promotion_apply.build_live_auth_promotion_preview",return_value=pv):
            with self.assertRaises(ValueError):
                build_live_auth_promotion_apply(
                    readiness(),ledger(),package(pv),
                    trusted_now="2026-11-03T21:13:00+00:00",
                )

    def test_unverified_package_rejected(self):
        p=package()
        p["package_status"]="UNVERIFIED"
        with self.assertRaises(ValueError):
            build_live_auth_promotion_apply(
                readiness(),ledger(),p,
                trusted_now="2026-11-03T21:13:00+00:00",
            )

if __name__=="__main__":
    unittest.main()
