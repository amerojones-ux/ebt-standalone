"""CLI for generating review-only evidence candidates from receipt files."""
import argparse
import hashlib
import json
import sys

from provider_receipt_review_candidate import build_review_candidate

MAX_RECEIPT_BYTES=65536

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("receipt")
    parser.add_argument("--expected-run-id",required=True)
    parser.add_argument("--expected-commit",required=True)
    args=parser.parse_args()
    try:
        with open(args.receipt,"rb") as handle:
            raw=handle.read(MAX_RECEIPT_BYTES+1)
        if len(raw)>MAX_RECEIPT_BYTES:
            raise ValueError("receipt file too large")
        artifact_sha256=hashlib.sha256(raw).hexdigest()
        receipt=json.loads(raw.decode("utf-8"))
        candidate=build_review_candidate(
            receipt,
            artifact_sha256=artifact_sha256,
            expected_run_id=args.expected_run_id,
            expected_commit=args.expected_commit,
        )
    except (OSError,ValueError,UnicodeDecodeError,json.JSONDecodeError) as exc:
        print("RECEIPT_REVIEW_CANDIDATE: HOLD")
        print("CHECK:",str(exc))
        return 1

    print("RECEIPT_REVIEW_CANDIDATE: REVIEW_ONLY")
    print(json.dumps(candidate,sort_keys=True))
    print("No readiness or evidence-ledger mutation performed.")
    return 0

if __name__=="__main__":
    sys.exit(main())
