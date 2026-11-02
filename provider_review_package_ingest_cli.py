"""CLI for strict signed GitHub review-package ingestion."""
import argparse
from datetime import datetime, timezone
import json

from provider_review_package_ingest import MAX_ZIP_BYTES, ingest_review_package

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("metadata")
    parser.add_argument("artifact_zip")
    parser.add_argument("--repository",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        with open(args.metadata,encoding="utf-8") as handle:
            metadata=json.load(handle)
        with open(args.artifact_zip,"rb") as handle:
            data=handle.read(MAX_ZIP_BYTES+1)
        if len(data)>MAX_ZIP_BYTES:
            raise ValueError("review artifact ZIP too large")
        result=ingest_review_package(
            metadata,
            data,
            repository=args.repository,
            trusted_now=datetime.now(timezone.utc).isoformat(),
        )
        with open(args.output,"w",encoding="utf-8") as handle:
            json.dump(result,handle,indent=2,sort_keys=True)
            handle.write("\n")
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("REVIEW_PACKAGE_INGEST: HOLD")
        print("CHECK:",str(exc))
        return 1
    print("REVIEW_PACKAGE_INGEST:",result["attested_status"])
    print("ATTESTED_DECISION_SHA256:",result["attested_decision_sha256"])
    print("No ledger, readiness, provider network, or forecast mutation performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
