"""CLI for generating exact SAFE_HOLD live-auth promotion files."""
import argparse
from datetime import datetime, timezone
import json
import pathlib

from provider_live_auth_promotion_apply import (
    build_live_auth_promotion_apply,
)

def _write(path,value):
    target=pathlib.Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("w",encoding="utf-8") as handle:
        json.dump(value,handle,indent=2,sort_keys=False)
        handle.write("\n")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("readiness")
    parser.add_argument("ledger")
    parser.add_argument("verified_package")
    parser.add_argument("--readiness-output",required=True)
    parser.add_argument("--ledger-output",required=True)
    parser.add_argument("--manifest-output",required=True)
    args=parser.parse_args()
    try:
        with open(args.readiness,encoding="utf-8") as handle:
            readiness=json.load(handle)
        with open(args.ledger,encoding="utf-8") as handle:
            ledger=json.load(handle)
        with open(args.verified_package,encoding="utf-8") as handle:
            package=json.load(handle)
        result=build_live_auth_promotion_apply(
            readiness,
            ledger,
            package,
            trusted_now=datetime.now(timezone.utc).isoformat(),
        )
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("LIVE_AUTH_PROMOTION_APPLY: HOLD")
        print("CHECK:",str(exc))
        return 1

    _write(args.readiness_output,result["updated_readiness"])
    _write(args.ledger_output,result["updated_ledger"])
    manifest={k:v for k,v in result.items() if k not in {
        "updated_readiness","updated_ledger"
    }}
    _write(args.manifest_output,manifest)
    print("LIVE_AUTH_PROMOTION_APPLY:",result["apply_status"])
    print("PROVIDER:",result["provider"])
    print("GLOBAL_PROVIDER_GATE:",result["global_provider_gate"])
    print("Forecast and network autorun remain disabled.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
