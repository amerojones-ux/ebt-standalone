"""CLI for dry-run evidence-ledger patch previews."""
import argparse
from datetime import datetime, timezone
import json

from provider_evidence_ledger_preview import build_ledger_preview

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("ledger")
    parser.add_argument("review_decision")
    args=parser.parse_args()

    try:
        with open(args.ledger,encoding="utf-8") as handle:
            ledger=json.load(handle)
        with open(args.review_decision,encoding="utf-8") as handle:
            decision=json.load(handle)
        result=build_ledger_preview(
            ledger,decision,trusted_now=datetime.now(timezone.utc).isoformat()
        )
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("EVIDENCE_LEDGER_PREVIEW: HOLD")
        print("CHECK:",str(exc))
        return 1

    print("EVIDENCE_LEDGER_PREVIEW:",result["preview_status"])
    print(json.dumps(result,sort_keys=True))
    print("No ledger, readiness, or forecast mutation performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
