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
            self.assertTrue(probe["exact_bundle_verification_required"])
            self.assertTrue(probe["github_api_verification_required"])
            self.assertTrue(probe["persisted_attestation_bundle_required"])
            self.assertTrue(probe["runner_pinned"])
            self.assertTrue(probe["python_toolchain_pinned"])
            self.assertTrue(probe["attestation_cli_capability_preflight_required"])
            self.assertTrue(probe["toolchain_fingerprint_bound"])
            self.assertTrue(probe["request_plan_fingerprint_bound"])
            self.assertTrue(probe["signed_presecret_execution_intent_required"])
            self.assertTrue(
                probe["execution_intent_dual_attestation_verification_required"]
            )
            self.assertTrue(
                probe["receipt_execution_intent_direct_binding_required"]
            )

    def test_marker_schema_downgrade_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '"schema_version": 4',
            '"schema_version": 3',
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_request_plan_fingerprint_binding_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '"request_plan_sha256": request_plan_sha256(',
            '"request_plan_sha256": "0"*64 + (',
        )
        result=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(result["status"],"INVALID_HOLD")

    def test_missing_toolchain_fingerprint_binding_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["The Odds API"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '"python_version": os.environ["TOOLCHAIN_PYTHON_VERSION"]',
            '"python_version": "3.13.0"',
        )
        r=assess_probe(
            "The Odds API",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_runner_label_drift_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "runs-on: ubuntu-24.04",
            "runs-on: ubuntu-latest",
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_floating_setup_python_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["The Odds API"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
            "actions/setup-python@v7",
        )
        r=assess_probe(
            "The Odds API",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_wrong_python_version_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["API-Sports"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            'python-version: "3.13"',
            'python-version: "3.12"',
        )
        r=assess_probe(
            "API-Sports",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_toolchain_gate_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "if: steps.toolchain.outputs.toolchain_verified == '1'",
            "if: always()",
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_receipt_execution_intent_binding_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '--execution-intent-sha256 "${{ steps.intent.outputs.intent_sha256 }}"',
            '--execution-intent-sha256 "0"',
        )
        result=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(result["status"],"INVALID_HOLD")

    def test_missing_execution_intent_gate_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "steps.verify_intent.outputs.intent_verified == '1'",
            "true",
        )
        result=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(result["status"],"INVALID_HOLD")

    def test_missing_execution_intent_dual_verification_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["The Odds API"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "/tmp/execution-intent-api-verification.json",
            "/tmp/missing-api-verification.json",
        )
        result=assess_probe(
            "The Odds API",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(result["status"],"INVALID_HOLD")

    def test_execution_intent_artifact_name_drift_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["API-Sports"]
        expected="name: "+spec["intent_prefix"]+"-${{ github.run_id }}"
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            expected,
            "name: wrong-execution-intent-${{ github.run_id }}",
        )
        result=assess_probe(
            "API-Sports",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(result["status"],"INVALID_HOLD")

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

    def test_missing_exact_bundle_verification_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '--bundle "$ATTESTATION_BUNDLE_PATH"',
            '--bundle "/tmp/untrusted.json"',
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_dual_verification_marker_modes_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["The Odds API"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            '"verification_modes": ["local_bundle", "github_api"]',
            '"verification_modes": ["github_api"]',
        )
        r=assess_probe(
            "The Odds API",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_persisted_bundle_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            'cp -- "$ATTESTATION_BUNDLE_PATH" "$BUNDLE_EXPORT_FILE"',
            'true',
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_bundle_artifact_name_drift_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["API-Sports"]
        expected="name: "+spec["bundle_prefix"]+"-${{ github.run_id }}"
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            expected,
            "name: wrong-bundle-${{ github.run_id }}",
        )
        r=assess_probe(
            "API-Sports",
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

    def test_missing_first_attempt_guard_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["WeatherAPI"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "github.run_attempt == 1",
            "github.run_attempt >= 1",
        )
        r=assess_probe(
            "WeatherAPI",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_missing_global_serialization_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["The Odds API"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "group: ebt-live-provider-probes",
            "group: provider-specific-probes",
        )
        r=assess_probe(
            "The Odds API",
            json_loader=lambda p:cfg[p],
            text_loader=lambda p:wfs[p],
        )
        self.assertEqual(r["status"],"INVALID_HOLD")

    def test_cancel_in_progress_invalidates_probe(self):
        cfg=configs(); wfs=workflows()
        spec=PROBES["API-Sports"]
        wfs[spec["workflow"]]=wfs[spec["workflow"]].replace(
            "cancel-in-progress: false",
            "cancel-in-progress: true",
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
