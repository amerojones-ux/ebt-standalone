"""Report fail-closed automated opportunity-discovery readiness from committed configs."""
import json
import sys
from pathlib import Path

from extensions.discovery_readiness import assess_discovery_readiness

ROOT=Path(__file__).resolve().parent


def load(name):
    with (ROOT/name).open(encoding="utf-8") as handle:
        return json.load(handle)


def main():
    try:
        result=assess_discovery_readiness(
            load("config/provider_readiness.json"),
            load("config/module_readiness_2026_10_30.json"),
            therundown_access=load("config/therundown_access.json"),
            theoddsapi_prop_ladder=load("config/theoddsapi_prop_ladder.json"),
            rapidapi_routing=load("config/rapidapi_routing.json"),
        )
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0 if result["status"] in {"SAFE_HOLD","READY_FOR_AUTOMATED_RESEARCH"} else 2
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"INVALID_HOLD","error":str(exc),"wager_status":"NOT APPROVED"}))
        return 2


if __name__=="__main__":
    sys.exit(main())
