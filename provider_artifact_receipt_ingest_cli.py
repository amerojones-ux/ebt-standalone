"""CLI for strict GitHub Actions receipt artifact ingestion."""
import argparse
import json

from provider_artifact_receipt_ingest import MAX_ZIP_BYTES, ingest_artifact_bytes

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("artifact_zip")
    parser.add_argument(
        "--provider",
        choices=["WeatherAPI","The Odds API","API-Sports"],
        required=True,
    )
    args=parser.parse_args()

    try:
        with open(args.artifact_zip,"rb") as handle:
            data=handle.read(MAX_ZIP_BYTES+1)
        if len(data)>MAX_ZIP_BYTES:
            raise ValueError("artifact ZIP too large")
        result=ingest_artifact_bytes(data,provider=args.provider)
    except (OSError,ValueError) as exc:
        print("PROVIDER_ARTIFACT_INGEST: HOLD")
        print("CHECK:",str(exc))
        return 1

    print("PROVIDER_ARTIFACT_INGEST:",result["ingestion_status"])
    print(json.dumps(result,sort_keys=True))
    print("No ledger, readiness, or forecast mutation performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
