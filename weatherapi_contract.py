"""Pure offline WeatherAPI response contract checks; no network or secrets."""
import math
import time

def validate_current(payload, expected_city, now_epoch=None, max_age_seconds=3600):
    errors = []
    if not isinstance(payload, dict):
        return ["response is not a JSON object"]
    loc, current = payload.get("location"), payload.get("current")
    if not isinstance(loc, dict) or not isinstance(current, dict):
        return ["location/current objects required"]
    city = loc.get("name")
    if not isinstance(city, str) or city.strip().casefold() != expected_city.strip().casefold():
        errors.append("location mismatch")
    epoch = current.get("last_updated_epoch")
    temp = current.get("temp_c")
    if type(epoch) not in (int, float) or not math.isfinite(epoch):
        errors.append("invalid observation timestamp")
    else:
        now = time.time() if now_epoch is None else now_epoch
        if epoch > now + 300 or now - epoch > max_age_seconds:
            errors.append("observation outside freshness window")
    if type(temp) not in (int, float) or not math.isfinite(temp) or not -100 <= temp <= 70:
        errors.append("invalid temperature")
    return errors
