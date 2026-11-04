"""Offline Sportradar NFL v7 auth/endpoint contract. No network or secrets."""
import re

GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
ALLOWED_ACCESS_LEVELS = {"UNKNOWN", "trial", "production"}

def validate_plan(plan):
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be object"]
    if plan.get("provider") != "Sportradar NFL":
        errors.append("provider mismatch")
    if plan.get("secret_name") != "EBT_SPORTRADAR_API_KEY":
        errors.append("secret mapping mismatch")
    if plan.get("auth_header") != "x-api-key":
        errors.append("auth header mismatch")
    if plan.get("host") != "api.sportradar.com":
        errors.append("host mismatch")
    if plan.get("version") != "v7":
        errors.append("version must be v7")
    if plan.get("language") != "en":
        errors.append("language must be en")
    if plan.get("format") != "json":
        errors.append("format must be json")
    if plan.get("access_level") not in ALLOWED_ACCESS_LEVELS:
        errors.append("invalid access level")
    if plan.get("account_registration_confirmed") is not True:
        errors.append("account registration not confirmed")
    if plan.get("subscription_details_verified") is not False:
        if plan.get("subscription_details_verified") is not True:
            errors.append("subscription details verification must be boolean")
    if plan.get("access_level_verified") is True and plan.get("access_level")=="UNKNOWN":
        errors.append("verified access level cannot be UNKNOWN")
    if plan.get("product_verified") is True and plan.get("subscription_details_verified") is not True:
        errors.append("product cannot be verified without subscription details")
    if plan.get("quota_reviewed") is True and plan.get("subscription_details_verified") is not True:
        errors.append("quota cannot be reviewed without subscription details")
    if plan.get("product_inventory_verified") is True and plan.get("subscription_details_verified") is not True:
        errors.append("product inventory cannot be verified without subscription details")
    if plan.get("network_enabled") is not False:
        errors.append("network must remain disabled")
    if plan.get("quota_impact_approved") is not False:
        errors.append("quota impact approval must remain false")
    if plan.get("request_count") != 0:
        errors.append("request count must be zero")
    if plan.get("forecast_enabled") is not False:
        errors.append("forecast must remain disabled")
    return errors

def validate_hierarchy(payload):
    """Validate a minimal NFL league hierarchy without storing venue/account details."""
    errors = []
    if not isinstance(payload, dict):
        return ["response must be object"]

    league = payload.get("league")
    conferences = payload.get("conferences")
    if not isinstance(league, dict):
        errors.append("league object required")
    else:
        if league.get("alias") != "NFL":
            errors.append("league alias mismatch")
        league_id = league.get("id")
        if not isinstance(league_id, str) or not GUID.fullmatch(league_id):
            errors.append("invalid league id")

    if not isinstance(conferences, list) or not conferences:
        errors.append("non-empty conferences list required")
        return errors

    aliases = set()
    team_ids = set()
    team_count = 0
    division_count = 0
    for conference in conferences:
        if not isinstance(conference, dict):
            errors.append("conference must be object")
            continue
        alias = conference.get("alias")
        if not isinstance(alias, str) or not alias:
            errors.append("conference alias required")
        elif alias in aliases:
            errors.append("duplicate conference alias")
        else:
            aliases.add(alias)
        divisions = conference.get("divisions")
        if not isinstance(divisions, list) or not divisions:
            errors.append("conference divisions required")
            continue
        division_count += len(divisions)
        for division in divisions:
            if not isinstance(division, dict):
                errors.append("division must be object")
                continue
            teams = division.get("teams")
            if not isinstance(teams, list) or not teams:
                errors.append("division teams required")
                continue
            for team in teams:
                if not isinstance(team, dict):
                    errors.append("team must be object")
                    continue
                team_id = team.get("id")
                team_alias = team.get("alias")
                if not isinstance(team_id, str) or not GUID.fullmatch(team_id):
                    errors.append("invalid team id")
                elif team_id in team_ids:
                    errors.append("duplicate team id")
                else:
                    team_ids.add(team_id)
                if not isinstance(team_alias, str) or not team_alias.strip():
                    errors.append("team alias required")
                team_count += 1

    if aliases != {"AFC", "NFC"}:
        errors.append("NFL hierarchy must contain AFC and NFC")
    if len(conferences) != 2:
        errors.append("NFL hierarchy must contain 2 conferences")
    if division_count != 8:
        errors.append("NFL hierarchy must contain 8 divisions")
    if team_count != 32:
        errors.append("NFL hierarchy must contain 32 teams")
    return errors

def can_authorize_first_request(plan):
    """Fail closed until access level and quota impact are separately confirmed."""
    if validate_plan(plan):
        return False
    return False
