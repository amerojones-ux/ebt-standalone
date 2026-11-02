"""CLI for preferred GitHub receipt+attestation artifact ingestion."""
import argparse
from datetime import datetime, timezone
import json

from provider_github_artifact_ingest import ingest_github_artifact

MAX_ZIP_BYTES=1024*1024

def _load_json(path):
    with open(path,encoding="utf-8") as handle:
        return json.load(handle)

def _load_bytes(path):
    with open(path,"rb") as handle:
        data=handle.read(MAX_ZIP_BYTES+1)
    if len(data)>MAX_ZIP_BYTES:
        raise ValueError("artifact ZIP too large")
    return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("receipt_metadata")
    parser.add_argument("receipt_zip")
    parser.add_argument("marker_metadata")
    parser.add_argument("marker_zip")
    parser.add_argument("--provider",required=True)
    parser.add_argument("--repository",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()

    try:
        result=ingest_github_artifact(
            _load_json(args.receipt_metadata),
            _load_bytes(args.receipt_zip),
            _load_json(args.marker_metadata),
            _load_bytes(args.marker_zip),
            provider=args.provider,
            repository=args.repository,
            trusted_now=datetime.now(timezone.utc).isoformat(),
        )
        candidate=result["candidate"]
        with open(args.output,"w",encoding="utf-8") as handle:
            json.dump(candidate,handle,indent=2,sort_keys=True)
            handle.write("\n")
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print("GITHUB_PROVIDER_EVIDENCE_INGEST: HOLD")
        print("CHECK:",str(exc))
        return 1

    print("GITHUB_PROVIDER_EVIDENCE_INGEST: REVIEW_ONLY")
    print("CANDIDATE_SHA256:",candidate["candidate_sha256"])
    print("No ledger, readiness, provider network, or forecast mutation performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
