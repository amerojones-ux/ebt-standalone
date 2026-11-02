"""Research-only batch validation for pregame forecasts."""
from datetime import datetime, timezone
from extensions.pregame_ledger_gate import validate_pregame_record

def validate_batch(records):
    if not isinstance(records, list) or not records:
        raise ValueError("nonempty list required")
    seen = set()
    events = {}
    validated = []
    for raw in records:
        item = validate_pregame_record(raw)
        fid = item["forecast_id"]
        if fid in seen:
            raise ValueError("duplicate forecast_id")
        seen.add(fid)
        start = datetime.fromisoformat(item["event_start"].replace("Z", "+00:00")).astimezone(timezone.utc)
        eid = item["event_id"]
        if eid in events and events[eid] != start:
            raise ValueError("inconsistent event start")
        events[eid] = start
        validated.append(item)
    return {"status": "HOLD_RESEARCH_ONLY", "records": validated,
            "forecast_count": len(validated), "event_count": len(events),
            "certified": False, "wager_approved": False}
