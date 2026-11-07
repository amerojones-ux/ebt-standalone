"""Synthetic tests for beneficiary opportunity-share redistribution."""
import unittest

from extensions.opportunity_reallocation import (
    allocate_displaced_opportunity,
    run_reallocation_scenarios,
)

CUTOFF="2026-11-07T18:00:00Z"


def roster(*,a_max="45",a_available="ACTIVE"):
    return [
        {
            "player_id":"OUT-1","availability":"OUT","baseline_units":"20",
            "max_units":"20","prior_alpha":"0","context_units":"0",
            "evidence_available_at":"2026-11-07T17:00:00Z",
        },
        {
            "player_id":"A","availability":a_available,"baseline_units":"30",
            "max_units":a_max,"prior_alpha":"4","context_units":"6",
            "evidence_available_at":"2026-11-07T17:00:00Z",
        },
        {
            "player_id":"B","availability":"ACTIVE","baseline_units":"25",
            "max_units":"40","prior_alpha":"3","context_units":"2",
            "evidence_available_at":"2026-11-07T17:00:00Z",
        },
        {
            "player_id":"C","availability":"ACTIVE","baseline_units":"25",
            "max_units":"35","prior_alpha":"2","context_units":"3",
            "evidence_available_at":"2026-11-07T17:00:00Z",
        },
    ]


class OpportunityReallocationTests(unittest.TestCase):
    def test_displaced_pool_is_shared_by_competing_beneficiaries(self):
        out=allocate_displaced_opportunity(
            roster(),metric="minutes",team_budget="100",cutoff=CUTOFF,
            redistribution_fraction="1",scenario_name="baseline")
        by={row["player_id"]:row for row in out["players"]}
        self.assertEqual(by["A"]["allocated_increment"],"10")
        self.assertEqual(by["B"]["allocated_increment"],"5")
        self.assertEqual(by["C"]["allocated_increment"],"5")
        self.assertEqual(out["allocated_units"],"20")
        self.assertEqual(out["team_contraction_or_unassigned_units"],"0")
        self.assertEqual(out["beneficiary_ranking"][0],"A")
        self.assertFalse(out["price_inputs_used"])

    def test_capacity_cap_forces_remaining_pool_to_other_players(self):
        out=allocate_displaced_opportunity(
            roster(a_max="33"),metric="minutes",team_budget="100",cutoff=CUTOFF,
            redistribution_fraction="1",scenario_name="cap")
        by={row["player_id"]:row for row in out["players"]}
        self.assertEqual(by["A"]["allocated_increment"],"3")
        self.assertAlmostEqual(float(by["B"]["allocated_increment"]),8.5)
        self.assertAlmostEqual(float(by["C"]["allocated_increment"]),8.5)
        self.assertAlmostEqual(float(out["allocated_units"]),20.0)

    def test_partial_redistribution_preserves_unassigned_team_units(self):
        out=allocate_displaced_opportunity(
            roster(),metric="touches",team_budget="100",cutoff=CUTOFF,
            redistribution_fraction=".5",scenario_name="adverse")
        self.assertEqual(out["target_redistributed_units"],"10.0")
        self.assertEqual(out["allocated_units"],"10.0")
        self.assertEqual(out["team_contraction_or_unassigned_units"],"10.0")

    def test_insufficient_capacity_does_not_force_impossible_allocation(self):
        rows=roster(a_max="31")
        rows[2]["max_units"]="26"
        rows[3]["max_units"]="26"
        out=allocate_displaced_opportunity(
            rows,metric="minutes",team_budget="100",cutoff=CUTOFF,
            redistribution_fraction="1",scenario_name="tight-caps")
        self.assertEqual(out["allocated_units"],"3")
        self.assertEqual(out["capacity_residual_from_target"],"17")
        self.assertEqual(out["team_contraction_or_unassigned_units"],"17")

    def test_post_cutoff_context_evidence_is_rejected(self):
        rows=roster()
        rows[1]["evidence_available_at"]="2026-11-07T18:00:01Z"
        with self.assertRaises(ValueError):
            allocate_displaced_opportunity(
                rows,metric="minutes",team_budget="100",cutoff=CUTOFF,
                redistribution_fraction="1",scenario_name="bad")

    def test_roster_baseline_must_reconcile_to_team_budget(self):
        rows=roster()
        rows[1]["baseline_units"]="31"
        with self.assertRaises(ValueError):
            allocate_displaced_opportunity(
                rows,metric="minutes",team_budget="100",cutoff=CUTOFF,
                redistribution_fraction="1",scenario_name="bad-budget")

    def test_active_player_requires_positive_concentration(self):
        rows=roster()
        rows[1]["prior_alpha"]="0"
        rows[1]["context_units"]="0"
        with self.assertRaises(ValueError):
            allocate_displaced_opportunity(
                rows,metric="minutes",team_budget="100",cutoff=CUTOFF,
                redistribution_fraction="1",scenario_name="no-evidence")

    def test_all_out_roster_keeps_entire_budget_unassigned(self):
        rows=roster()
        for row in rows:
            row["availability"]="OUT"
        out=allocate_displaced_opportunity(
            rows,metric="minutes",team_budget="100",cutoff=CUTOFF,
            redistribution_fraction="1",scenario_name="all-out")
        self.assertEqual(out["allocated_units"],"0")
        self.assertEqual(out["team_contraction_or_unassigned_units"],"100")

    def test_scenario_comparison_exposes_beneficiary_floor_and_ceiling(self):
        specs={
            "baseline":{
                "redistribution_fraction":"1",
                "availability_overrides":{},
            },
            "adverse":{
                "redistribution_fraction":".5",
                "availability_overrides":{},
            },
            "secondary_out":{
                "redistribution_fraction":"1",
                "availability_overrides":{"B":"OUT"},
            },
        }
        out=run_reallocation_scenarios(
            roster(),specs,metric="minutes",team_budget="100",cutoff=CUTOFF)
        self.assertEqual(out["scenario_count"],3)
        a=next(x for x in out["player_stability"] if x["player_id"]=="A")
        self.assertGreater(float(a["increment_ceiling"]),float(a["increment_floor"]))
        self.assertTrue(a["positive_increment_all_scenarios"])
        b=next(x for x in out["player_stability"] if x["player_id"]=="B")
        self.assertFalse(b["positive_increment_all_scenarios"])

    def test_unknown_scenario_player_override_is_rejected(self):
        with self.assertRaises(ValueError):
            run_reallocation_scenarios(
                roster(),
                {"x":{
                    "redistribution_fraction":"1",
                    "availability_overrides":{"UNKNOWN":"OUT"},
                }},
                metric="minutes",team_budget="100",cutoff=CUTOFF)

    def test_extra_sportsbook_field_is_rejected_by_exact_schema(self):
        rows=roster()
        rows[1]["sportsbook_line"]="35.5"
        with self.assertRaises(ValueError):
            allocate_displaced_opportunity(
                rows,metric="minutes",team_budget="100",cutoff=CUTOFF,
                redistribution_fraction="1",scenario_name="market-contaminated")


if __name__=="__main__":
    unittest.main()
