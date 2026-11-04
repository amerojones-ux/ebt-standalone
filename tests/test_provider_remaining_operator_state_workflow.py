import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/provider-remaining-operator-state.yml"
VALIDATION=ROOT/".github/workflows/validation.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"

class RemainingProviderOperatorStateWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")
        cls.validation=VALIDATION.read_text(encoding="utf-8")

    def test_manual_protected_first_attempt_only(self):
        text=self.text
        self.assertIn("workflow_dispatch:",text)
        self.assertIn("github.run_attempt == 1",text)
        self.assertIn("github.ref_protected == true",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertNotIn("schedule:",text)
        self.assertNotIn("\npush:",text)
        self.assertNotIn("pull_request:",text)

    def test_permissions_are_read_only_plus_attestation(self):
        text=self.text
        self.assertIn("  contents: read",text)
        self.assertIn("  id-token: write",text)
        self.assertIn("  attestations: write",text)
        self.assertIn("  artifact-metadata: write",text)
        self.assertNotIn("contents: write",text)
        self.assertNotIn("actions: write",text)
        self.assertNotIn("pull-requests: write",text)
        self.assertNotIn("secrets.",text)
        self.assertNotIn("EBT_",text)

    def test_pinned_actions_and_immutable_checkout(self):
        text=self.text
        needle="ref: " + "$" + "{{ github.sha }}"
        self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
        self.assertIn("actions/attest@"+ATTEST_SHA,text)
        self.assertIn("actions/upload-artifact@"+UPLOAD_SHA,text)
        self.assertIn(needle,text)
        self.assertIn("persist-credentials: false",text)
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',text)
        self.assertIn('test -z "$(git status --porcelain)"',text)

    def test_state_must_keep_network_and_forecast_blocked(self):
        text=self.text
        self.assertIn("remaining-provider operator state invalid",text)
        self.assertIn("forecast unexpectedly enabled",text)
        self.assertIn("network autorun unexpectedly enabled",text)
        self.assertIn("provider request unexpectedly unblocked",text)

    def test_status_is_attested_and_short_lived(self):
        text=self.text
        self.assertIn("subject-path: remaining_provider_operator_state.json",text)
        self.assertIn("gh attestation verify remaining_provider_operator_state.json",text)
        self.assertIn(
            ".github/workflows/provider-remaining-operator-state.yml",
            text,
        )
        self.assertIn("remaining_provider_operator_state_attestation.json",text)
        self.assertIn("retention-days: 7",text)
        self.assertIn("if-no-files-found: error",text)

    def test_workflow_has_no_provider_or_repository_mutation(self):
        text=self.text
        for fragment in (
            "curl ","wget ","requests.","urllib.request","git push",
            "gh pr","contents: write",
        ):
            self.assertNotIn(fragment,text)

    def test_validation_enforces_operator_state(self):
        self.assertIn(
            "Assert remaining-provider operator state is valid and fail-closed",
            self.validation,
        )
        self.assertIn(
            "python provider_remaining_operator_state_cli.py",
            self.validation,
        )

if __name__=="__main__":
    unittest.main()
