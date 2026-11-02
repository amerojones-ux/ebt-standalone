import unittest
from sportradar_nfl_contract import validate_hierarchy, validate_plan, can_authorize_first_request

PLAN = {
    "provider":"Sportradar NFL",
    "secret_name":"EBT_SPORTRADAR_API_KEY",
    "auth_header":"x-api-key",
    "host":"api.sportradar.com",
    "version":"v7",
    "language":"en",
    "format":"json",
    "access_level":"UNKNOWN",
    "network_enabled":False,
    "quota_impact_approved":False,
    "request_count":0,
    "forecast_enabled":False,
}

def hierarchy():
    teams=[]
    for i in range(32):
        teams.append({"id":f"00000000-0000-4000-8000-{i:012x}","alias":f"T{i:02d}"})
    return {
        "league":{"id":"3c6d318a-6164-4290-9bbc-bf9bb21cc4b8","alias":"NFL"},
        "conferences":[
            {"alias":"AFC","divisions":[{"teams":teams[:16]}]},
            {"alias":"NFC","divisions":[{"teams":teams[16:]}]},
        ],
    }

class SportradarNflContractTests(unittest.TestCase):
    def test_safe_plan(self):
        self.assertEqual(validate_plan(PLAN), [])

    def test_wrong_header_holds(self):
        p=dict(PLAN,auth_header="Authorization")
        self.assertTrue(validate_plan(p))

    def test_network_enable_holds(self):
        p=dict(PLAN,network_enabled=True)
        self.assertTrue(validate_plan(p))

    def test_quota_approval_cannot_be_flipped_in_offline_plan(self):
        p=dict(PLAN,quota_impact_approved=True)
        self.assertTrue(validate_plan(p))

    def test_request_count_must_stay_zero(self):
        p=dict(PLAN,request_count=1)
        self.assertTrue(validate_plan(p))

    def test_valid_hierarchy(self):
        self.assertEqual(validate_hierarchy(hierarchy()), [])

    def test_wrong_league_holds(self):
        p=hierarchy(); p["league"]["alias"]="NCAA"
        self.assertTrue(validate_hierarchy(p))

    def test_duplicate_team_holds(self):
        p=hierarchy(); p["conferences"][1]["divisions"][0]["teams"][0]["id"]=p["conferences"][0]["divisions"][0]["teams"][0]["id"]
        self.assertTrue(validate_hierarchy(p))

    def test_team_count_must_be_32(self):
        p=hierarchy(); p["conferences"][1]["divisions"][0]["teams"].pop()
        self.assertTrue(validate_hierarchy(p))

    def test_first_request_is_never_authorized_by_offline_contract(self):
        self.assertFalse(can_authorize_first_request(PLAN))

if __name__=="__main__":
    unittest.main()
