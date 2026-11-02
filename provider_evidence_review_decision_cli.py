"""CLI for explicit review of provider evidence candidates."""
import argparse
from datetime import datetime, timezone
import json
import sys

from provider_evidence_review_decision import review_candidate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("candidate")
    parser.add_argument("--decision",choices=["APPROVE","REJECT"],required=True)
    parser.add_argument("--reviewer",required=True)
    parser.add_argument("--reviewed-at")
    parser.add_argument("--output")
    args=parser.parse_args()

    reviewed_at=args.reviewed_at or datetime.now(timezone.utc).isoformat()
    trusted_now=datetime.now(timezone.utc).isoformat()

    try:
        with open(args.candidate,encoding="utf-8") as handle:
            candidate=json.load(handle)
        result=review_candidate(
            candidate,
            decision=args.decision,
            reviewer=args.reviewer,
            reviewed_at=reviewed_at,
            trusted_now=trusted_now,
        )
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("EVIDENCE_REVIEW_DECISION: HOLD")
        print("CHECK:",str(exc))
        return 1

    if args.output:
        with open(args.output,"w",encoding="utf-8") as handle:
            json.dump(result,handle,indent=2,sort_keys=True)
            handle.write("\n")
    print("EVIDENCE_REVIEW_DECISION:",result["proposal_status"])
    print(json.dumps(result,sort_keys=True))
    print("No evidence-ledger, readiness, or forecast mutation performed.")
    return 0

if __name__=="__main__":
    sys.exit(main())
