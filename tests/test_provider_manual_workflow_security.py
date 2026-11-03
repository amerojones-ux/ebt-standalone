import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS=ROOT/".github"/"workflows"

OFFLINE_CHECKOUT_WORKFLOWS={
    "live-provider-approval-gate.yml":"ebt-live-provider-approval-gate",
    "provider-activation-gate.yml":"ebt-provider-activation-gate",
    "provider-offline-preflight.yml":"ebt-provider-offline-preflight",
    "weatherapi-execution-gate.yml":"ebt-weatherapi-execution-gate",
}
SECRET_PRESENCE="provider-secret-presence.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"

class ProviderManualWorkflowSecurityTests(unittest.TestCase):
    def _read(self,name):
        return (WORKFLOWS/name).read_text(encoding="utf-8")

    def _assert_common_manual_gate(self,text,group):
        self.assertIn("workflow_dispatch:",text)
        self.assertNotIn("schedule:",text)
        self.assertNotIn("pull_request:",text)
        self.assertNotIn("\npush:",text)
        self.assertNotIn("\n  push:",text)
        self.assertIn("github.run_attempt == 1",text)
        self.assertIn("github.ref_protected == true",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertIn("runs-on: ubuntu-24.04",text)
        self.assertIn(
            "concurrency:\n  group: "+group+"\n  cancel-in-progress: false",
            text,
        )
        self.assertIn("permissions:\n  contents: read",text)
        self.assertNotIn("contents: write",text)
        self.assertNotIn("actions: write",text)
        self.assertNotIn("git push",text)
        self.assertNotIn("gh pr",text)

    def test_offline_checkout_workflows_use_immutable_protected_main(self):
        for name,group in OFFLINE_CHECKOUT_WORKFLOWS.items():
            with self.subTest(workflow=name):
                text=self._read(name)
                self._assert_common_manual_gate(text,group)
                self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
                self.assertIn("ref: ${{ github.sha }}",text)
                self.assertNotIn("ref: main",text)
                self.assertIn("persist-credentials: false",text)
                self.assertIn("Verify immutable source checkout",text)
                self.assertIn(
                    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
                    text,
                )
                self.assertIn(
                    'test -z "$(git status --porcelain)"',
                    text,
                )
                self.assertNotIn("secrets.",text)

    def test_secret_presence_requires_explicit_consent_before_secret_env(self):
        text=self._read(SECRET_PRESENCE)
        self._assert_common_manual_gate(
            text,
            "ebt-provider-secret-presence",
        )
        self.assertIn("confirm_presence_review:",text)
        self.assertIn("I_APPROVE_PROVIDER_SECRET_PRESENCE_CHECK",text)
        self.assertIn(
            "inputs.confirm_presence_review == "
            "'I_APPROVE_PROVIDER_SECRET_PRESENCE_CHECK'",
            text,
        )
        prefix=text.split("    steps:",1)[0]
        self.assertNotIn("\n    env:",prefix)
        self.assertIn("      - name: Report presence only",text)
        self.assertIn("        env:",text)
        for secret in (
            "EBT_THERUNDOWN_API_KEY",
            "EBT_SPORTSDATA_API_KEY",
            "EBT_THEODDS_API_KEY",
            "EBT_APISPORTS_API_KEY",
            "EBT_RAPIDAPI_API_KEY",
            "EBT_WEATHER_API_KEY",
            "EBT_SPORTRADAR_API_KEY",
        ):
            self.assertIn("secrets."+secret,text)

    def test_secret_presence_has_no_network_or_value_logging_path(self):
        text=self._read(SECRET_PRESENCE)
        lowered=text.lower()
        for forbidden in (
            "curl ",
            "wget ",
            "urllib",
            "requests.",
            "http://",
            "https://",
            "print(os.environ",
        ):
            self.assertNotIn(forbidden,lowered)
        self.assertIn("PRESENT",text)
        self.assertIn("MISSING_OR_DIFFERENT_NAME",text)
        self.assertIn("No endpoint requests made.",text)

if __name__=="__main__":
    unittest.main()
