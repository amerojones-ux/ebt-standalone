import copy
import json
import unittest

from apisports_status_receipt import build_receipt
from provider_receipt_review_candidate import (
    bind_attestation_verification,
    build_review_candidate,
)
from provider_evidence_review_decision import review_candidate
from provider_live_auth_promotion_preview import (
    build_live_auth_promotion_preview,
)

COMMIT="a"*40
RUN="12345"
ARTIFACT="d"*64
MARKER="e"*64
REPO="amerojones-ux/ebt-standalone"
ATTESTATION_ID="attestation-123"
ATTESTATION_URL="https://github.com/"+REPO+"/attestations/"+ATTESTATION_ID
SIGNER=".github/workflows/apisports-status-probe.yml"
NOW="2026-11-02T21:00:00+00:00"
REVIEWED="2026-11-02T20:59:00+00:00"

def readiness():
    with open("config/provider_readiness.json",encoding="utf-8") as handle:
        return json.load(handle)

def ledger():
    with open("config/provider_evidence.json",encoding="utf-8") as handle:
        return json.load(handle)

def decision():
    receipt=build_receipt(
        {"status":"PASS","category":"authenticated_status_schema"},
        "2026-11-02T20:58:00+00:00",COMMIT,RUN
    )
    pending=build_review_candidate(
        receipt,
        artifact_sha256=ARTIFACT,
        expected_run_id=RUN,
        expected_commit=COMMIT,
    )
    candidate=bind_attestation_verification(
        pending,
        marker_sha256=MARKER,
        source_repository=REPO,
        attestation_id=ATTESTATION_ID,
        attestation_url=ATTESTATION_URL,
        signer_workflow=SIGNER,
    )
    return review_candidate(
        candidate,
        decision="APPROVE",
        reviewer="authorized-reviewer",
        reviewed_at=REVIEWED,
        trusted_now=NOW,
    )

class ProviderLiveAuthPromotionPreviewTests(unittest.TestCase):
    def test_preview_sets_only_live_auth_and_stays_safe_hold(self):
        original=readiness()
        result=build_live_auth_promotion_preview(
            original,ledger(),decision(),trusted_now=NOW
        )
        self.assertEqual(
            result["preview_status"],
            "VALID_LIVE_AUTH_PROMOTION_PREVIEW",
        )
        self.assertEqual(result["provider"],"API-Sports")
        self.assertEqual(result["global_provider_gate"],"SAFE_HOLD")
        self.assertFalse(result["ledger_write_permitted"])
        self.assertFalse(result["readiness_write_permitted"])
        self.assertFalse(result["forecast_activation_permitted"])
        self.assertEqual(len(result["preview_sha256"]),64)

        before=next(
            x for x in original["providers"] if x["name"]=="API-Sports"
        )
        after=next(
            x for x in result["preview_readiness"]["providers"]
            if x["name"]=="API-Sports"
        )
        self.assertFalse(before["live_auth_verified"])
        self.assertTrue(after["live_auth_verified"])
        for key,value in before.items():
            if key!="live_auth_verified":
                self.assertEqual(after[key],value)

        self.assertFalse(original["forecast_enabled"])
        self.assertFalse(result["preview_readiness"]["forecast_enabled"])
        self.assertEqual(original["required_providers"],[])
        self.assertEqual(result["preview_readiness"]["required_providers"],[])

    def test_original_inputs_are_not_mutated(self):
        r=readiness()
        l=ledger()
        r_before=copy.deepcopy(r)
        l_before=copy.deepcopy(l)
        build_live_auth_promotion_preview(r,l,decision(),trusted_now=NOW)
        self.assertEqual(r,r_before)
        self.assertEqual(l,l_before)

    def test_existing_live_auth_true_cannot_be_overwritten(self):
        r=readiness()
        for entry in r["providers"]:
            if entry["name"]=="API-Sports":
                entry["live_auth_verified"]=True
        with self.assertRaises(ValueError):
            build_live_auth_promotion_preview(
                r,ledger(),decision(),trusted_now=NOW
            )

    def test_rejected_decision_cannot_promote(self):
        approved=decision()
        approved["decision"]="REJECT"
        with self.assertRaises(ValueError):
            build_live_auth_promotion_preview(
                readiness(),ledger(),approved,trusted_now=NOW
            )

    def test_preview_refuses_activation_boundary_crossing(self):
        r=readiness()
        r["required_providers"]=["API-Sports"]
        r["model_gates"]={
            "source_provenance_verified":True,
            "roster_injury_identity_verified":True,
            "historical_calibration_verified":True,
            "joint_dependence_verified":True,
        }
        for entry in r["providers"]:
            if entry["name"]=="API-Sports":
                entry["entitlement_verified"]=True
                entry["identity_verified"]=True
                entry["freshness_verified"]=True
                entry["model_evidence_allowed"]=True

        # Missing evidence for those already-true claims must fail closed
        # before live-auth can accidentally become an activation trigger.
        with self.assertRaises(ValueError):
            build_live_auth_promotion_preview(
                r,ledger(),decision(),trusted_now=NOW
            )

if __name__=="__main__":
    unittest.main()
