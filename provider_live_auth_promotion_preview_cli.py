"""CLI for non-mutating live-auth promotion previews."""
import argparse
from datetime import datetime, timezone
import json

from provider_live_auth_promotion_preview import (
    build_live_auth_promotion_preview,
)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("readiness")
    parser.add_argument("ledger")
    parser.add_argument("review_decision")
    args=parser.parse_args()

    try:
        with open(args.readiness,encoding="utf-8") as handle:
            readiness=json.load(handle)
        with open(args.ledger,encoding="utf-8") as handle:
            ledger=json.load(handle)
        with open(args.review_decision,encoding="utf-8") as handle:
            decision=json.load(handle)
        result=build_live_auth_promotion_preview(
            readiness,
            ledger,
            decision,
            trusted_now=datetime.now(timezone.utc).isoformat(),
        )
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("LIVE_AUTH_PROMOTION_PREVIEW: HOLD")
        print("CHECK:",str(exc))
        return 1

    print("LIVE_AUTH_PROMOTION_PREVIEW:",result["preview_status"])
    print("GLOBAL_PROVIDER_GATE:",result["global_provider_gate"])
    print(json.dumps(result,sort_keys=True))
    print("No ledger, readiness, network, or forecast mutation performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
