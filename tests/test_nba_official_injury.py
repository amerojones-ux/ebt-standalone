"""Synthetic regression tests for official NBA injury-report contracts."""
import unittest

from extensions.nba_official_injury import (
    assess_game_injury_gate,
    bind_canonical_identities,
    diff_official_reports,
    latest_report_before,
    parse_official_injury_index,
    validate_extracted_report,
)

URL_400="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-07_04_00AM.pdf"
URL_415="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-07_04_15AM.pdf"
CAPTURE="2026-11-07T09:16:00Z"
EVENT_KEY="2026-11-07|AAA@BBB"
SCHEDULE={EVENT_KEY:{"event_id":"NBA-GAME-1","event_start_utc":"2026-11-07T23:00:00Z"}}
TEAM_IDS={"Alpha Team":"T-A","Beta Team":"T-B"}
PLAYER_IDS={
    "Alpha Team|Player, One":"P-1",
    "Beta Team|Player, Two":"P-2",
}


def rows(alpha_status="Questionable", beta_submission="SUBMITTED"):
    out=[
        {
            "game_date":"11/07/2026","game_time_et":"06:00","matchup":"AAA@BBB",
            "team":"Alpha Team","player_name":"Player, One",
            "current_status":alpha_status,"reason":"Injury/Illness - Synthetic",
            "submission_status":"SUBMITTED",
        }
    ]
    if beta_submission=="NOT_YET_SUBMITTED":
        out.append({
            "game_date":"11/07/2026","game_time_et":"06:00","matchup":"AAA@BBB",
            "team":"Beta Team","player_name":None,"current_status":None,
            "reason":None,"submission_status":"NOT_YET_SUBMITTED",
        })
    else:
        out.append({
            "game_date":"11/07/2026","game_time_et":"06:00","matchup":"AAA@BBB",
            "team":"Beta Team","player_name":"Player, Two",
            "current_status":"Probable","reason":"Injury/Illness - Synthetic 2",
            "submission_status":"SUBMITTED",
        })
    return out


def canonical(source_rows, url=URL_415):
    normalized=validate_extracted_report(source_rows,report_url=url,captured_at=CAPTURE)
    return bind_canonical_identities(
        normalized,team_ids=TEAM_IDS,player_ids=PLAYER_IDS,event_schedule=SCHEDULE)


class NBAOfficialInjuryTests(unittest.TestCase):
    def test_index_parser_accepts_only_official_injury_pdf_links(self):
        html=f'''
        <a href="{URL_400}">4:00</a>
        <a href="{URL_415}">4:15</a>
        <a href="https://example.com/Injury-Report_2026-11-07_04_30AM.pdf">bad</a>
        '''
        out=parse_official_injury_index(html)
        self.assertEqual(len(out),2)
        self.assertTrue(out[-1]["report_url"].endswith("04_15AM.pdf"))

    def test_latest_report_respects_cutoff_and_does_not_use_future_file(self):
        reports=parse_official_injury_index(
            f'<a href="{URL_400}">4:00</a><a href="{URL_415}">4:15</a>')
        out=latest_report_before(reports,"2026-11-07T09:10:00Z")
        self.assertTrue(out["report_url"].endswith("04_00AM.pdf"))

    def test_report_rows_preserve_official_status_and_reason(self):
        out=validate_extracted_report(rows(),report_url=URL_415,captured_at=CAPTURE)
        first=out["rows"][0]
        self.assertEqual(first["current_status"],"Questionable")
        self.assertEqual(first["reason"],"Injury/Illness - Synthetic")
        self.assertEqual(out["source_authority"],"A1_OFFICIAL")
        self.assertFalse(out["pdf_extraction_verified_by_this_module"])

    def test_not_yet_submitted_is_team_state_not_player_status(self):
        out=validate_extracted_report(
            rows(beta_submission="NOT_YET_SUBMITTED"),
            report_url=URL_415,captured_at=CAPTURE)
        beta=out["rows"][1]
        self.assertEqual(beta["row_type"],"TEAM_NOT_SUBMITTED")
        self.assertIsNone(beta["current_status"])

    def test_exact_identity_and_schedule_binding_passes(self):
        out=canonical(rows())
        self.assertTrue(out["identity_verified"])
        self.assertTrue(all(x["schedule_verified"] for x in out["rows"]))
        self.assertTrue(all(x["pregame_eligible"] for x in out["rows"]))
        self.assertEqual(out["rows"][0]["event_id"],"NBA-GAME-1")

    def test_missing_player_identity_fails_closed_without_fuzzy_match(self):
        normalized=validate_extracted_report(rows(),report_url=URL_415,captured_at=CAPTURE)
        out=bind_canonical_identities(
            normalized,team_ids=TEAM_IDS,
            player_ids={"Alpha Team|Player One":"WRONG-FUZZY"},
            event_schedule=SCHEDULE)
        self.assertFalse(out["identity_verified"])
        self.assertTrue(any(x["kind"]=="PLAYER_IDENTITY" for x in out["identity_holds"]))

    def test_missing_schedule_fails_identity_gate(self):
        normalized=validate_extracted_report(rows(),report_url=URL_415,captured_at=CAPTURE)
        out=bind_canonical_identities(
            normalized,team_ids=TEAM_IDS,player_ids=PLAYER_IDS,event_schedule={})
        self.assertFalse(out["identity_verified"])
        self.assertTrue(any(x["kind"]=="EVENT_SCHEDULE" for x in out["identity_holds"]))

    def test_status_change_requires_full_rerun(self):
        previous=canonical(rows(alpha_status="Questionable"),url=URL_400)
        current=canonical(rows(alpha_status="Out"),url=URL_415)
        out=diff_official_reports(previous,current)
        self.assertTrue(out["full_rerun_required"])
        self.assertTrue(any(x["kind"]=="PLAYER_STATUS_CHANGE" for x in out["changes"]))

    def test_team_submission_transition_requires_rerun(self):
        previous=canonical(rows(beta_submission="NOT_YET_SUBMITTED"),url=URL_400)
        current=canonical(rows(beta_submission="SUBMITTED"),url=URL_415)
        out=diff_official_reports(previous,current)
        self.assertTrue(out["full_rerun_required"])
        self.assertTrue(any(x["kind"]=="TEAM_REPORT_SUBMITTED" for x in out["changes"]))

    def test_not_submitted_team_forces_game_hold(self):
        current=canonical(rows(beta_submission="NOT_YET_SUBMITTED"))
        out=assess_game_injury_gate(
            current,event_key=EVENT_KEY,cutoff="2026-11-07T09:20:00Z",
            max_report_age_minutes=30)
        self.assertEqual(out["status"],"HOLD")
        self.assertIn("TEAM_REPORT_NOT_YET_SUBMITTED",out["reasons"])

    def test_fresh_submitted_two_team_report_clears_role_input_gate(self):
        current=canonical(rows())
        out=assess_game_injury_gate(
            current,event_key=EVENT_KEY,cutoff="2026-11-07T09:20:00Z",
            max_report_age_minutes=30)
        self.assertEqual(out["status"],"FOUND")
        self.assertEqual(out["reasons"],[])
        self.assertEqual(out["wager_status"],"NOT APPROVED")

    def test_stale_report_holds(self):
        current=canonical(rows(),url=URL_400)
        out=assess_game_injury_gate(
            current,event_key=EVENT_KEY,cutoff="2026-11-07T10:00:00Z",
            max_report_age_minutes=30)
        self.assertEqual(out["status"],"HOLD")
        self.assertIn("REPORT_STALE_AT_CUTOFF",out["reasons"])


if __name__=="__main__":
    unittest.main()
