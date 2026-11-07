"""Offline The Odds API per-event player-prop ladder contract.

Implements documented request planning, response normalization, and posted-ladder
coverage accounting. No network calls, credential reads, calibration, forecasts,
or wager approvals occur here.
"""
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

SPORT_KEY_RE = re.compile(r"^[a-z0-9_]+$")
EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
REGION_RE = re.compile(r"^[a-z0-9_]+$")
BOOK_RE = re.compile(r"^[a-z0-9_-]+$")
PLAYER_PREFIXES = ("player_", "batter_", "pitcher_")
ODDS_FORMAT = "american"
DATE_FORMAT = "iso"


def _clock(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return parsed.astimezone(timezone.utc)


def is_player_market_key(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and SPORT_KEY_RE.fullmatch(value) is not None
        and value.startswith(PLAYER_PREFIXES)
    )


def _sport_event(sport: Any, event_id: Any) -> Tuple[str, str]:
    if not isinstance(sport, str) or SPORT_KEY_RE.fullmatch(sport) is None:
        raise ValueError("canonical The Odds API sport key required")
    if not isinstance(event_id, str) or EVENT_ID_RE.fullmatch(event_id) is None:
        raise ValueError("canonical event id required")
    return sport, event_id


def _regions(regions: Sequence[str]) -> Tuple[str, ...]:
    if not isinstance(regions, (list, tuple)) or not regions:
        raise ValueError("nonempty regions required")
    out = []
    for region in regions:
        if not isinstance(region, str) or REGION_RE.fullmatch(region) is None:
            raise ValueError("invalid region key")
        if region in out:
            raise ValueError("duplicate region key")
        out.append(region)
    return tuple(out)


def _markets(markets: Sequence[str]) -> Tuple[str, ...]:
    if not isinstance(markets, (list, tuple)) or not markets:
        raise ValueError("nonempty player market keys required")
    out = []
    for market in markets:
        if not is_player_market_key(market):
            raise ValueError("player/batter/pitcher market key required")
        if market in out:
            raise ValueError("duplicate market key")
        out.append(market)
    return tuple(out)


def public_event_markets_request(sport: str, event_id: str, regions: Sequence[str]) -> Dict[str, Any]:
    """Plan the documented event-markets discovery call without the API key."""
    sport, event_id = _sport_event(sport, event_id)
    regions = _regions(regions)
    return {
        "method": "GET",
        "scheme": "https",
        "host": "api.the-odds-api.com",
        "path": f"/v4/sports/{sport}/events/{event_id}/markets",
        "query": {"regions": ",".join(regions), "dateFormat": DATE_FORMAT},
        "credential_query_key": "apiKey",
        "network_enabled": False,
        "purpose": "discover_recently_seen_event_market_keys",
    }


def public_event_odds_requests(
    sport: str,
    event_id: str,
    regions: Sequence[str],
    market_keys: Sequence[str],
    *,
    max_markets_per_request: int = 10,
) -> List[Dict[str, Any]]:
    """Create bounded event-odds request chunks for all requested player markets."""
    sport, event_id = _sport_event(sport, event_id)
    regions = _regions(regions)
    markets = _markets(market_keys)
    if type(max_markets_per_request) is not int or not 1 <= max_markets_per_request <= 50:
        raise ValueError("max_markets_per_request must be integer 1..50")
    plans = []
    for start in range(0, len(markets), max_markets_per_request):
        chunk = markets[start:start + max_markets_per_request]
        plans.append({
            "method": "GET",
            "scheme": "https",
            "host": "api.the-odds-api.com",
            "path": f"/v4/sports/{sport}/events/{event_id}/odds",
            "query": {
                "regions": ",".join(regions),
                "markets": ",".join(chunk),
                "oddsFormat": ODDS_FORMAT,
                "dateFormat": DATE_FORMAT,
            },
            "credential_query_key": "apiKey",
            "market_keys": list(chunk),
            "estimated_usage_credits": len(chunk) * len(regions),
            "network_enabled": False,
            "purpose": "fetch_event_player_prop_ladder",
        })
    return plans


def parse_event_markets(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize recently seen market keys per bookmaker for one event."""
    if not isinstance(payload, Mapping):
        raise ValueError("event-markets response object required")
    event_id = payload.get("id")
    sport = payload.get("sport_key")
    _sport_event(sport, event_id)
    commence = _clock(payload.get("commence_time"), "commence_time").isoformat()
    bookmakers = payload.get("bookmakers")
    if not isinstance(bookmakers, list):
        raise ValueError("bookmakers list required")
    rows = []
    seen_books = set()
    for book in bookmakers:
        if not isinstance(book, Mapping):
            raise ValueError("bookmaker object required")
        key = book.get("key")
        if not isinstance(key, str) or BOOK_RE.fullmatch(key) is None or key in seen_books:
            raise ValueError("unique bookmaker key required")
        seen_books.add(key)
        markets = book.get("markets")
        if not isinstance(markets, list):
            raise ValueError("bookmaker markets list required")
        keys = []
        for item in markets:
            market_key = item.get("key") if isinstance(item, Mapping) else None
            if not isinstance(market_key, str) or SPORT_KEY_RE.fullmatch(market_key) is None:
                raise ValueError("market key required")
            if market_key in keys:
                raise ValueError("duplicate market key for bookmaker")
            keys.append(market_key)
        rows.append({
            "bookmaker_key": key,
            "bookmaker_title": str(book.get("title") or ""),
            "market_keys": sorted(keys),
            "player_market_keys": sorted(k for k in keys if is_player_market_key(k)),
        })
    return {
        "event_id": event_id,
        "sport_key": sport,
        "commence_time": commence,
        "bookmakers": rows,
        "discovery_semantics": "recently_seen_market_keys_not_global_supported_market_catalog",
    }


def _american_price(value: Any) -> int:
    if isinstance(value, bool) or type(value) not in (int, float):
        raise ValueError("numeric American price required")
    if int(value) != value:
        raise ValueError("integer American price required")
    price = int(value)
    if -100 < price < 100:
        raise ValueError("American price must be <= -100 or >= +100")
    return price


def parse_event_odds(payload: Mapping[str, Any], *, captured_at: str) -> Dict[str, Any]:
    """Normalize all player-prop outcomes without collapsing alternate thresholds."""
    if not isinstance(payload, Mapping):
        raise ValueError("event-odds response object required")
    event_id = payload.get("id")
    sport = payload.get("sport_key")
    _sport_event(sport, event_id)
    captured = _clock(captured_at, "captured_at")
    commence = _clock(payload.get("commence_time"), "commence_time")
    if captured >= commence:
        raise ValueError("pregame prop capture must precede event start")
    bookmakers = payload.get("bookmakers")
    if not isinstance(bookmakers, list):
        raise ValueError("bookmakers list required")

    records = []
    identities = set()
    for book in bookmakers:
        if not isinstance(book, Mapping):
            raise ValueError("bookmaker object required")
        book_key = book.get("key")
        if not isinstance(book_key, str) or BOOK_RE.fullmatch(book_key) is None:
            raise ValueError("valid bookmaker key required")
        markets = book.get("markets")
        if not isinstance(markets, list):
            raise ValueError("markets list required")
        for market in markets:
            if not isinstance(market, Mapping):
                raise ValueError("market object required")
            market_key = market.get("key")
            if not is_player_market_key(market_key):
                continue
            updated = _clock(market.get("last_update"), "market.last_update")
            if updated > captured:
                raise ValueError("market update cannot be after capture")
            outcomes = market.get("outcomes")
            if not isinstance(outcomes, list) or not outcomes:
                raise ValueError("nonempty outcomes required")
            for outcome in outcomes:
                if not isinstance(outcome, Mapping):
                    raise ValueError("outcome object required")
                selection = outcome.get("name")
                player = outcome.get("description")
                if not isinstance(selection, str) or not selection.strip():
                    raise ValueError("outcome selection required")
                if not isinstance(player, str) or not player.strip():
                    raise ValueError("player description required")
                point_raw = outcome.get("point")
                point = None if point_raw is None else Decimal(str(point_raw))
                if point is not None and not point.is_finite():
                    raise ValueError("finite point required")
                price = _american_price(outcome.get("price"))
                identity = (book_key, market_key, player, selection, str(point))
                if identity in identities:
                    raise ValueError("duplicate exact ladder outcome")
                identities.add(identity)
                records.append({
                    "event_id": event_id,
                    "sport_key": sport,
                    "commence_time": commence.isoformat(),
                    "bookmaker_key": book_key,
                    "bookmaker_title": str(book.get("title") or ""),
                    "market_key": market_key,
                    "player_name": player,
                    "selection": selection,
                    "point": None if point is None else str(point),
                    "american_odds": price,
                    "market_last_update": updated.isoformat(),
                    "captured_at": captured.isoformat(),
                    "source": "THE_ODDS_API_EVENT_ODDS",
                })
    return {
        "event_id": event_id,
        "sport_key": sport,
        "commence_time": commence.isoformat(),
        "records": records,
        "record_count": len(records),
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
    }


def assess_posted_ladder_coverage(
    discovery: Mapping[str, Any],
    parsed_odds_payloads: Iterable[Mapping[str, Any]],
    requested_market_keys: Sequence[str],
) -> Dict[str, Any]:
    """Verify every discovered requested bookmaker/market pair was captured."""
    requested = set(_markets(requested_market_keys))
    if not isinstance(discovery, Mapping):
        raise ValueError("parsed discovery object required")
    event_id = discovery.get("event_id")
    sport = discovery.get("sport_key")
    _sport_event(sport, event_id)

    expected_pairs = set()
    discovered_player = set()
    for book in discovery.get("bookmakers", []):
        book_key = book.get("bookmaker_key")
        for market in book.get("player_market_keys", []):
            discovered_player.add(market)
            if market in requested:
                expected_pairs.add((book_key, market))

    seen_pairs = set()
    row_count = 0
    payload_count = 0
    for payload in parsed_odds_payloads:
        if not isinstance(payload, Mapping):
            raise ValueError("parsed odds payload object required")
        if payload.get("event_id") != event_id or payload.get("sport_key") != sport:
            raise ValueError("event/sport mismatch across prop ladder captures")
        payload_count += 1
        for row in payload.get("records", []):
            market = row.get("market_key")
            if market in requested:
                seen_pairs.add((row.get("bookmaker_key"), market))
                row_count += 1

    missing_pairs = sorted(expected_pairs - seen_pairs)
    unexpected_pairs = sorted(seen_pairs - expected_pairs)
    posted_requested = sorted(discovered_player & requested)
    not_seen_as_posted = sorted(requested - discovered_player)
    complete = not missing_pairs and not unexpected_pairs
    return {
        "mode": "THE_ODDS_API_POSTED_PROP_LADDER_COVERAGE",
        "event_id": event_id,
        "sport_key": sport,
        "requested_market_keys": sorted(requested),
        "discovered_requested_market_keys": posted_requested,
        "requested_not_seen_as_posted": not_seen_as_posted,
        "expected_bookmaker_market_pairs": len(expected_pairs),
        "captured_bookmaker_market_pairs": len(seen_pairs),
        "normalized_outcome_rows": row_count,
        "parsed_odds_payload_count": payload_count,
        "missing_bookmaker_market_pairs": [list(x) for x in missing_pairs],
        "unexpected_bookmaker_market_pairs": [list(x) for x in unexpected_pairs],
        "complete_posted_ladder_verified": complete,
        "global_supported_market_catalog_complete": False,
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
        "note": (
            "Completeness is relative to player-market keys recently seen for this event/bookmaker "
            "at the discovery snapshot, not every market supported globally by the provider."
        ),
    }
