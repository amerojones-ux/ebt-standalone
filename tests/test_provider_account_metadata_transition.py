import unittest

from provider_account_metadata_transition import build_transition

class ProviderAccountMetadataTransitionTests(unittest.TestCase):
    def assert_safe_preview(self,result):
        self.assertEqual(
            result["status"],
            "VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW",
            msg=result.get("errors"),
        )
        self.assertFalse(result["write_permitted"])
        self.assertFalse(result["network_request_permitted"])
        self.assertFalse(result["forecast_activation_permitted"])
        self.assertFalse(result["model_evidence_allowed"])

    def test_sportsdataio_reconciled_transition_is_proposal_only(self):
        result=build_transition("SportsDataIO",{
            "source_type":"PROVIDER_SUPPORT",
            "scope_status":"RECONCILED",
            "product_name":"NFL League API",
            "feed_scope":"Scores",
            "endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        self.assert_safe_preview(result)
        cfg=result["candidate_configs"]["SportsDataIO"]
        self.assertTrue(cfg["trial_scope_reconciled"])
        self.assertEqual(cfg["official_scope_status"],"RECONCILED")
        self.assertFalse(cfg["network_enabled"])
        self.assertFalse(cfg["model_evidence_allowed"])
        rec=next(
            p for p in result["candidate_registry"]["providers"]
            if p["name"]=="SportsDataIO"
        )
        self.assertTrue(rec["exact_product_verified"])
        self.assertTrue(rec["exact_feed_verified"])
        self.assertFalse(rec["live_request_permitted"])

    def test_sportsdataio_conflict_cannot_be_silently_reconciled(self):
        result=build_transition("SportsDataIO",{
            "source_type":"ACCOUNT_PORTAL",
            "scope_status":"CONFLICTING",
            "product_name":"NFL League API",
            "feed_scope":"Scores",
            "endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("scope must be explicitly reconciled",result["errors"][0])

    def test_sportradar_trial_transition_derives_exact_hierarchy_endpoint(self):
        result=build_transition("Sportradar",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        })
        self.assert_safe_preview(result)
        cfg=result["candidate_configs"]["Sportradar"]
        self.assertEqual(cfg["access_level"],"trial")
        self.assertEqual(
            cfg["probe_endpoint"],
            "https://api.sportradar.com/nfl/official/trial/v7/en/league/hierarchy.json",
        )
        self.assertTrue(cfg["product_verified"])
        self.assertTrue(cfg["access_level_verified"])
        self.assertFalse(cfg["network_enabled"])
        self.assertFalse(cfg["quota_impact_approved"])

    def test_sportradar_non_nfl_product_is_rejected(self):
        result=build_transition("Sportradar",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"MLB API",
            "package_name":"Base",
            "access_level":"trial",
            "quota_reviewed":True,
        })
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("must explicitly identify NFL",result["errors"][0])

    def test_rapidapi_ambiguous_all_product_is_rejected(self):
        result=build_transition("RapidAPI",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"all",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREE",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://example-sports.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("ambiguous name rejected",result["errors"][0])

    def test_rapidapi_exact_route_transition_is_proposal_only(self):
        result=build_transition("RapidAPI",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"Example Sports Provider",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREEMIUM",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://example-sports.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        self.assert_safe_preview(result)
        cfg=result["candidate_configs"]["RapidAPI"]
        self.assertEqual(cfg["rapidapi_host"],"example-sports.p.rapidapi.com")
        self.assertEqual(
            cfg["probe_endpoint"],
            "https://example-sports.p.rapidapi.com/v1/status",
        )
        self.assertTrue(cfg["endpoint_reviewed"])
        self.assertFalse(cfg["network_enabled"])
        rec=next(
            p for p in result["candidate_registry"]["providers"]
            if p["name"]=="RapidAPI"
        )
        self.assertTrue(rec["exact_product_verified"])
        self.assertTrue(rec["exact_host_verified"])
        self.assertTrue(rec["exact_endpoint_verified"])
        self.assertFalse(rec["live_request_permitted"])

    def test_rapidapi_endpoint_must_match_host_and_have_no_query(self):
        result=build_transition("RapidAPI",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"Example Sports Provider",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREE",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://wrong.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("endpoint host mismatch",result["errors"][0])

        result=build_transition("RapidAPI",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"Example Sports Provider",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREE",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://example-sports.p.rapidapi.com/v1/status?key=x",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("endpoint query/fragment forbidden",result["errors"][0])

    def test_unapproved_source_or_extra_sensitive_field_is_rejected(self):
        result=build_transition("Sportradar",{
            "source_type":"WEB_SEARCH",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        })
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("source_type",result["errors"][0])

        result=build_transition("Sportradar",{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
            "api_key":"forbidden",
        })
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("unsupported fact fields",result["errors"][0])

if __name__=="__main__":
    unittest.main()
