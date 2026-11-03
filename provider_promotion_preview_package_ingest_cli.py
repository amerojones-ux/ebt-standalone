"""CLI for strict signed promotion-preview package ingestion."""
import argparse
from datetime import datetime, timezone
import json

from provider_promotion_preview_package_ingest import (
    ingest_promotion_preview_package,
)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("metadata")
    parser.add_argument("zip_file")
    parser.add_argument("--repository",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        with open(args.metadata,encoding="utf-8") as handle:
            metadata=json.load(handle)
        with open(args.zip_file,"rb") as handle:
            zip_bytes=handle.read()
        result=ingest_promotion_preview_package(
            metadata,
            zip_bytes,
            repository=args.repository,
            trusted_now=datetime.now(timezone.utc).isoformat(),
        )
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("PROMOTION_PREVIEW_PACKAGE_INGEST: HOLD")
        print("CHECK:",str(exc))
        return 1
    with open(args.output,"w",encoding="utf-8") as handle:
        json.dump(result,handle,indent=2,sort_keys=True)
        handle.write("\n")
    print("PROMOTION_PREVIEW_PACKAGE_INGEST:",result["package_status"])
    print("PROVIDER:",result["provider"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
