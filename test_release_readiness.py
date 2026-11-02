import unittest
from dataclasses import replace
from release_readiness import ReleaseEvidence, State, decide, all_unverified, REQUIRED

ALL_PASS = ReleaseEvidence(*(State.PASS for _ in REQUIRED))
class ReleaseReadinessTests(unittest.TestCase):
    def test_no_evidence_holds(self):
        result = decide(all_unverified())
        self.assertEqual(result.status, "HOLD")
        self.assertEqual(len(result.blockers), len(REQUIRED))
    def test_every_gate_required(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                for state in (State.HOLD, State.FAIL, State.NOT_TESTED):
                    result = decide(replace(ALL_PASS, **{name:state}))
                    self.assertEqual(result.status, "HOLD")
                    self.assertIn(name, result.blockers)
    def test_all_pass_requires_release_review(self):
        self.assertEqual(decide(ALL_PASS).status, "READY_FOR_CONTROLLED_RELEASE_REVIEW")
    def test_no_automatic_production_approval(self):
        self.assertNotEqual(decide(ALL_PASS).status, "PRODUCTION_APPROVED")

if __name__ == "__main__":
    unittest.main()
