import json
import unittest

from provider_probe_readiness_registry import PROBES, assess_all, assess_probe

def configs():
    result={}
    for spec in PROBES.values():
        with open(spec["config"],encoding="utf-8") as handle:
            result[spec["config"]]=json.load(handle)
    return result

def workflows():
    result={}
    for spec in PROBES.values():
        with open(spec["workflow"],encoding="utf-8") as handle:
            result[spec["workflow"]]=handle.read()
    return result

class ProviderProbeReadinessRegistryTests(unittest.TestCase):
    def test_committed_registry_is_prepared_default_deny(self):
        result=assess_all()
        self.assertEqual(result["status"],"PREPARED_DEFAULT_DENY")
        self.assertEqual(result["probe_count"],3)
        for probe in result["probes"]:
            self.assertEqual(probe["status"],"PREPARED_DEFAULT_DENY")
            self.assertTrue(probe["manual_dispatch_required"])
            self.assertFalse(probe["committed_request_approval"])
            self.assertFalse(probe["execution_claimed"])
            self.assertTrue(probe["signed_provenance_required"])
            self.assertTrue(probe["cryptographic_verification_required"])

    def test_network_enable_drift_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["API-Sports"]
        cfg[spec["config"]]["network_enabled"]=True
        r=assess_probe(
            "API-Sports",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_manual_default_no_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace('default: "NO"','default: "YES"')
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_artifact_pinning_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["The Odds API"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9",
            "actions/upload-artifact@v7",
        )
        r=assess_probe(
            "The Odds API",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_or_floating_attestation_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6",
            "actions/attest@v4",
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_source_digest_verification_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '--source-digest "$GITHUB_SHA"',
            '--source-digest "untrusted"',
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_signer_workflow_verification_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["API-Sports"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '--signer-workflow "$GITHUB_REPOSITORY/$SIGNER_WORKFLOW"',
            '--owner amerojones-ux',
        )
        r=assess_probe(
            "API-Sports",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_schedule_trigger_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]+="\nschedule:\n"
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_secret_mapping_drift_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["API-Sports"]
        cfg[spec["config"]]["secret_name"]="WRONG"
        r=assess_probe(
            "API-Sports",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

if __name__=="__main__":
    unittest.main()
