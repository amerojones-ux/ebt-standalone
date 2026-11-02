"""CLI for generating review-only evidence candidates from provider receipts."""
import argparse
import json
import sys

from provider_receipt_review_candidate import build_review_candidate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("receipt")
    args=parser.parse_args()
    try:
        with open(args.receipt,encoding="utf-8") as handle:
            receipt=json.load(handle)
        candidate=build_review_candidate(receipt)
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("RECEIPT_REVIEW_CANDIDATE: HOLD")
        print("CHECK:",str(exc))
        return 1

    print("RECEIPT_REVIEW_CANDIDATE: REVIEW_ONLY")
    print(json.dumps(candidate,sort_keys=True))
    print("No readiness or evidence-ledger mutation performed.")
    return 0

if __name__=="__main__":
    sys.exit(main())
