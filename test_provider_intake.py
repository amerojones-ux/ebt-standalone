import unittest
from dataclasses import replace
from provider_intake import PROVIDERS, ProviderIntake, IntakeStatus, evaluate_intake, untested_inventory

GOOD=ProviderIntake("WeatherAPI","api.weatherapi.com","forecast","v1",True,True,True,True,True,"evidence-1")
class ProviderIntakeTests(unittest.TestCase):
    def test_inventory_complete(self): self.assertEqual(tuple(x.provider for x in untested_inventory()),PROVIDERS)
    def test_inventory_not_tested(self):
        for p in untested_inventory():
            self.assertEqual(evaluate_intake(p)[0],IntakeStatus.NOT_TESTED)
    def test_all_verified(self): self.assertEqual(evaluate_intake(GOOD)[0],IntakeStatus.VERIFIED)
    def test_unknown_provider(self): self.assertEqual(evaluate_intake(replace(GOOD,provider="Unknown"))[0],IntakeStatus.FAIL)
    def test_missing_host(self): self.assertEqual(evaluate_intake(replace(GOOD,api_host=None))[0],IntakeStatus.NOT_TESTED)
    def test_missing_evidence(self): self.assertEqual(evaluate_intake(replace(GOOD,evidence_id=None))[0],IntakeStatus.HOLD)
    def test_missing_authentication(self): self.assertEqual(evaluate_intake(replace(GOOD,source_authenticated=None))[0],IntakeStatus.HOLD)
    def test_explicit_failure(self): self.assertEqual(evaluate_intake(replace(GOOD,schema_pass=False))[0],IntakeStatus.FAIL)
    def test_missing_credential(self): self.assertEqual(evaluate_intake(replace(GOOD,credential_present=None))[0],IntakeStatus.HOLD)
if __name__=="__main__": unittest.main()
