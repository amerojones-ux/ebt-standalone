"""Pure, credential-free WeatherAPI transport-result classification. No HTTP calls."""
from weatherapi_contract import validate_current

def classify(status, payload, expected_city, now_epoch):
    if type(status) is not int:
        return "HOLD_TRANSPORT"
    if status in (401, 403):
        return "HOLD_AUTH"
    if status == 429:
        return "HOLD_RATE_LIMIT"
    if status in (301, 302, 303, 307, 308):
        return "HOLD_REDIRECT"
    if status != 200:
        return "HOLD_HTTP"
    if validate_current(payload, expected_city, now_epoch):
        return "HOLD_DATA"
    return "SCHEMA_ACCEPTED_OFFLINE"
