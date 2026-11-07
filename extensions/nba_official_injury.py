"""NBA official injury-report ingestion contracts for Black Diamond.

The NBA publishes continual injury-report PDFs linked from official.nba.com.
This module resolves report links, validates already-extracted structured rows,
binds exact canonical identities, and emits fail-closed status-delta/rerun gates.

PDF byte-to-text extraction is intentionally outside this module. An extractor
must preserve source URL, report timestamp, capture time and row provenance.
No network calls, OCR, fuzzy identity, forecasts or wager approval occur here.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
INDEX_HOST = "official.nba.com"
PDF_HOST = "ak-static.cms.nba.com"
PDF_PATH_PREFIX = "/referee/injury/"
INDEX_PATH = "/nba-injury-report-2026-27-season"
PDF_RE = re.compile(
    r"^/referee/injury/Injury-Report_(?P<date>\d{4}-\d{2}-\d{2})_"
    r"(?P<hour>\d{2})_(?P<minute>\d{2})(?P<ampm>AM|PM)\.pdf$"
)
MATCHUP_RE = re.compile(r"^[A-Z]{2,4}@[A-Z]{2,4}$")
TIME_RE = re.compile(r"^(?:0[1-9]|1[0-2]):[0-5]\d$")
STATUSES = {"Available", "Probable", "Questionable", "Doubtful", "Out"}
SUBMISSION = {"SUBMITTED", "NOT_YET_SUBMITTED"}


def _clock(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return dt.astimezone(timezone.utc)


def _date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} date string required")
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"{field} invalid date")


def _report_time_from_url(url: str) -> datetime:
    if not isinstance(url, str) or not url:
        raise ValueError("report URL required")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != PDF_HOST:
        raise ValueError("official NBA injury PDF host required")
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.query or parsed.fragment:
        raise ValueError("invalid official injury PDF URL")
    m = PDF_RE.fullmatch(parsed.path)
    if not m:
        raise ValueError("unsupported injury PDF filename")
    raw = f"{m.group('date')} {m.group('hour')}:{m.group('minute')} {m.group('ampm')}"
    return datetime.strptime(raw, "%Y-%m-%d %I:%M %p").replace(tzinfo=EASTERN)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if isinstance(href, str) and href.strip():
            self.links.append(href.strip())


def parse_official_injury_index(html: str, *, base_url: str = "https://official.nba.com") -> List[Dict[str, str]]:
    """Return unique official PDF links sorted chronologically."""
    if not isinstance(html, str) or not html.strip():
        raise ValueError("injury index HTML required")
    base = urlsplit(base_url)
    if base.scheme != "https" or base.hostname != INDEX_HOST:
        raise ValueError("official NBA base URL required")
    parser = _Links()
    parser.feed(html)
    found = {}
    for href in parser.links:
        absolute = urljoin(base_url, href)
        try:
            report_time = _report_time_from_url(absolute)
        except ValueError:
            continue
        key = report_time.astimezone(timezone.utc).isoformat()
        found[key] = absolute
    return [
        {
            "report_url": found[key],
            "report_time_utc": key,
            "report_time_et": _report_time_from_url(found[key]).isoformat(),
        }
        for key in sorted(found)
    ]


def latest_report_before(reports: Sequence[Mapping[str, Any]], cutoff: str) -> Dict[str, Any]:
    at = _clock(cutoff, "cutoff")
    candidates = []
    for row in reports:
        if not isinstance(row, Mapping):
            raise ValueError("report index rows must be objects")
        stamp = _clock(row.get("report_time_utc"), "report_time_utc")
        url = row.get("report_url")
        if _report_time_from_url(url).astimezone(timezone.utc) != stamp:
            raise ValueError("report URL/timestamp mismatch")
        if stamp <= at:
            candidates.append((stamp, dict(row)))
    if not candidates:
        raise ValueError("no official injury report available at or before cutoff")
    return max(candidates, key=lambda x: x[0])[1]


def _event_start(game_date: str, game_time_et: str) -> datetime:
    date_iso = _date(game_date, "game_date")
    if not isinstance(game_time_et, str) or TIME_RE.fullmatch(game_time_et.strip()) is None:
        raise ValueError("game_time_et must be HH:MM 12-hour clock without suffix")
    # Official report times are ET; game_time rows are also labeled ET.
    raw = datetime.strptime(f"{date_iso} {game_time_et.strip()}", "%Y-%m-%d %I:%M")
    return raw.replace(tzinfo=EASTERN)


def validate_extracted_report(
    rows: Iterable[Mapping[str, Any]],
    *,
    report_url: str,
    captured_at: str,
) -> Dict[str, Any]:
    """Validate fully expanded rows from a trusted PDF text/table extraction."""
    report_time = _report_time_from_url(report_url)
    captured = _clock(captured_at, "captured_at")
    if report_time.astimezone(timezone.utc) > captured:
        raise ValueError("report cannot be captured before publication timestamp")
    if not isinstance(rows, Iterable):
        raise ValueError("rows iterable required")

    normalized = []
    identities = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise ValueError("injury row object required")
        required = {
            "game_date", "game_time_et", "matchup", "team",
            "player_name", "current_status", "reason", "submission_status",
        }
        if set(raw) != required:
            raise ValueError("exact extracted injury-row schema required")
        game_date = _date(raw["game_date"], "game_date")
        game_time = raw["game_time_et"]
        start = _event_start(game_date, game_time)
        matchup = raw["matchup"]
        team = raw["team"]
        submission = raw["submission_status"]
        if not isinstance(matchup, str) or MATCHUP_RE.fullmatch(matchup.strip()) is None:
            raise ValueError("canonical matchup code required")
        if not isinstance(team, str) or not team.strip():
            raise ValueError("team name required")
        if submission not in SUBMISSION:
            raise ValueError("invalid submission_status")

        player = raw["player_name"]
        status = raw["current_status"]
        reason = raw["reason"]
        if submission == "NOT_YET_SUBMITTED":
            if player not in (None, "") or status not in (None, "") or reason not in (None, ""):
                raise ValueError("not-submitted team row cannot contain player status")
            row_type = "TEAM_NOT_SUBMITTED"
            player = None
            status = None
            reason = None
        else:
            if not isinstance(player, str) or not player.strip():
                raise ValueError("submitted row requires player_name")
            if status not in STATUSES:
                raise ValueError("unsupported NBA injury status")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("submitted row requires reason")
            row_type = "PLAYER_STATUS"
            player = player.strip()
            reason = reason.strip()

        identity = (game_date, game_time, matchup.strip(), team.strip(), player)
        if identity in identities:
            raise ValueError("duplicate injury-report row")
        identities.add(identity)
        normalized.append({
            "row_type": row_type,
            "game_date": game_date,
            "game_time_et": game_time.strip(),
            "event_start_utc": start.astimezone(timezone.utc).isoformat(),
            "matchup": matchup.strip(),
            "team": team.strip(),
            "player_name": player,
            "current_status": status,
            "reason": reason,
            "submission_status": submission,
            "report_url": report_url,
            "report_time_utc": report_time.astimezone(timezone.utc).isoformat(),
            "captured_at": captured.isoformat(),
            "pregame_eligible": captured < start.astimezone(timezone.utc),
        })
    if not normalized:
        raise ValueError("nonempty extracted injury report required")
    return {
        "mode": "NBA_OFFICIAL_INJURY_REPORT_NORMALIZED",
        "source_authority": "A1_OFFICIAL",
        "report_url": report_url,
        "report_time_utc": report_time.astimezone(timezone.utc).isoformat(),
        "captured_at": captured.isoformat(),
        "rows": normalized,
        "row_count": len(normalized),
        "pdf_extraction_verified_by_this_module": False,
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
    }


def bind_canonical_identities(
    normalized_report: Mapping[str, Any],
    *,
    team_ids: Mapping[str, str],
    player_ids: Mapping[str, str],
) -> Dict[str, Any]:
    """Bind exact team/player names; fuzzy matching is forbidden."""
    if not isinstance(normalized_report, Mapping) or not isinstance(normalized_report.get("rows"), list):
        raise ValueError("normalized report required")
    if not isinstance(team_ids, Mapping) or not isinstance(player_ids, Mapping):
        raise ValueError("team_ids and player_ids mappings required")
    resolved = []
    holds = []
    for row in normalized_report["rows"]:
        team = row["team"]
        team_id = team_ids.get(team)
        if not isinstance(team_id, str) or not team_id.strip():
            holds.append({"kind": "TEAM_IDENTITY", "team": team})
            team_id = None
        player_id = None
        if row["row_type"] == "PLAYER_STATUS":
            key = f"{team}|{row['player_name']}"
            player_id = player_ids.get(key)
            if not isinstance(player_id, str) or not player_id.strip():
                holds.append({"kind": "PLAYER_IDENTITY", "key": key})
                player_id = None
        resolved.append({
            **row,
            "team_id": team_id,
            "player_id": player_id,
            "event_key": f"{row['game_date']}|{row['matchup']}",
            "identity_verified": bool(team_id and (row["row_type"] == "TEAM_NOT_SUBMITTED" or player_id)),
        })
    return {
        "mode": "NBA_OFFICIAL_INJURY_IDENTITY_BINDING",
        "rows": resolved,
        "identity_holds": holds,
        "identity_verified": not holds,
        "forecast_status": "HOLD" if holds else "RESEARCH_INPUT",
        "wager_status": "NOT APPROVED",
    }


def diff_official_reports(previous: Mapping[str, Any], current: Mapping[str, Any]) -> Dict[str, Any]:
    """Compare canonical bound reports without inferring missing-player availability."""
    for name, report in (("previous", previous), ("current", current)):
        if not isinstance(report, Mapping) or not isinstance(report.get("rows"), list):
            raise ValueError(f"{name} canonical report required")
    def team_submission(report):
        out = {}
        for row in report["rows"]:
            key = (row["event_key"], row["team_id"] or row["team"])
            state = row["submission_status"]
            if key in out and out[key] != state:
                raise ValueError("conflicting team submission state")
            out[key] = state
        return out
    def players(report):
        out = {}
        for row in report["rows"]:
            if row["row_type"] != "PLAYER_STATUS":
                continue
            key = (row["event_key"], row["team_id"] or row["team"], row["player_id"] or row["player_name"])
            if key in out:
                raise ValueError("duplicate canonical player status")
            out[key] = row
        return out

    prev_team, cur_team = team_submission(previous), team_submission(current)
    prev_players, cur_players = players(previous), players(current)
    changes = []
    rerun = False
    hold = False

    for key in sorted(set(prev_team) | set(cur_team), key=str):
        a, b = prev_team.get(key), cur_team.get(key)
        if a != b:
            kind = "TEAM_REPORT_SUBMITTED" if a == "NOT_YET_SUBMITTED" and b == "SUBMITTED" else "TEAM_SUBMISSION_STATE_CHANGE"
            changes.append({"kind": kind, "key": list(key), "before": a, "after": b})
            rerun = True
        if b == "NOT_YET_SUBMITTED":
            hold = True

    for key in sorted(set(prev_players) | set(cur_players), key=str):
        a, b = prev_players.get(key), cur_players.get(key)
        if a is None and b is not None:
            changes.append({
                "kind": "PLAYER_ADDED_TO_REPORT", "key": list(key),
                "before": None, "after": b["current_status"],
            })
            rerun = True
        elif a is not None and b is None:
            changes.append({
                "kind": "PLAYER_REMOVED_REQUIRES_CONFIRMATION", "key": list(key),
                "before": a["current_status"], "after": None,
            })
            rerun = True
            hold = True
        elif a and b and (a["current_status"] != b["current_status"] or a["reason"] != b["reason"]):
            changes.append({
                "kind": "PLAYER_STATUS_CHANGE", "key": list(key),
                "before": a["current_status"], "after": b["current_status"],
                "reason_before": a["reason"], "reason_after": b["reason"],
            })
            rerun = True

    return {
        "mode": "NBA_OFFICIAL_INJURY_REPORT_DIFF",
        "changes": changes,
        "change_count": len(changes),
        "full_rerun_required": rerun,
        "hold_for_confirmation": hold,
        "forecast_status": "HOLD" if hold else ("RERUN_REQUIRED" if rerun else "UNCHANGED"),
        "wager_status": "NOT APPROVED",
    }


def assess_game_injury_gate(
    canonical_report: Mapping[str, Any],
    *,
    event_key: str,
    cutoff: str,
    max_report_age_minutes: int,
) -> Dict[str, Any]:
    """Require fresh official report, both teams submitted, and exact identities."""
    if type(max_report_age_minutes) is not int or max_report_age_minutes <= 0:
        raise ValueError("positive max_report_age_minutes required")
    at = _clock(cutoff, "cutoff")
    rows = [
        row for row in canonical_report.get("rows", [])
        if row.get("event_key") == event_key
    ]
    if not rows:
        return {
            "event_key": event_key, "status": "HOLD",
            "reasons": ["EVENT_NOT_PRESENT_IN_REPORT"],
            "forecast_status": "HOLD", "wager_status": "NOT APPROVED",
        }
    report_time = _clock(rows[0]["report_time_utc"], "report_time_utc")
    captured = _clock(rows[0]["captured_at"], "captured_at")
    reasons = []
    if captured > at:
        reasons.append("REPORT_CAPTURE_AFTER_CUTOFF")
    age = (at - report_time).total_seconds() / 60
    if age < 0 or age > max_report_age_minutes:
        reasons.append("REPORT_STALE_AT_CUTOFF")
    if any(not row.get("pregame_eligible") for row in rows):
        reasons.append("REPORT_NOT_PREGAME_ELIGIBLE")
    if any(row.get("identity_verified") is not True for row in rows):
        reasons.append("CANONICAL_IDENTITY_UNRESOLVED")

    teams = {}
    for row in rows:
        key = row.get("team_id") or row.get("team")
        state = row["submission_status"]
        if key in teams and teams[key] != state:
            reasons.append("CONFLICTING_TEAM_SUBMISSION_STATE")
        teams[key] = state
    if len(teams) != 2:
        reasons.append("BOTH_TEAMS_NOT_IDENTIFIED")
    if any(state != "SUBMITTED" for state in teams.values()):
        reasons.append("TEAM_REPORT_NOT_YET_SUBMITTED")

    return {
        "mode": "NBA_OFFICIAL_INJURY_GAME_GATE",
        "event_key": event_key,
        "status": "FOUND" if not reasons else "HOLD",
        "report_age_minutes": age,
        "teams": teams,
        "reasons": sorted(set(reasons)),
        "full_role_rerun_required_on_change": True,
        "forecast_status": "RESEARCH_INPUT" if not reasons else "HOLD",
        "wager_status": "NOT APPROVED",
    }
