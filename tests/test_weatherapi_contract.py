import unittest
from weatherapi_contract import validate_current

NOW = 1800000000
def sample():
    return {"location": {"name": "Chicago"}, "current": {"last_updated_epoch": NOW - 900, "temp_c": 12.5}}

class WeatherApiContractTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate_current(sample(), "Chicago", NOW), [])
    def test_wrong_city(self): self.assertTrue(validate_current(sample(), "Boston", NOW))
    def test_missing_current(self):
        p=sample(); del p["current"]; self.assertTrue(validate_current(p, "Chicago", NOW))
    def test_stale(self):
        p=sample(); p["current"]["last_updated_epoch"]=NOW-7200; self.assertTrue(validate_current(p,"Chicago",NOW))
    def test_future(self):
        p=sample(); p["current"]["last_updated_epoch"]=NOW+7200; self.assertTrue(validate_current(p,"Chicago",NOW))
    def test_boolean_temperature(self):
        p=sample(); p["current"]["temp_c"]=True; self.assertTrue(validate_current(p,"Chicago",NOW))
    def test_nan(self):
        p=sample(); p["current"]["temp_c"]=float("nan"); self.assertTrue(validate_current(p,"Chicago",NOW))
    def test_non_object(self): self.assertTrue(validate_current([], "Chicago", NOW))

if __name__ == "__main__": unittest.main()
