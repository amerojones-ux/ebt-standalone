"""Offline CLI for immutable daily Black Diamond audit ledgers."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.immutable_daily_audit import (
    append_daily_audit_record,
    artifact_ref_from_receipt,
    summarize_daily_audit,
    validate_audit_payload,
    validate_daily_audit_chain,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    p=Path(path)
    if not p.exists():
        return []
    rows=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(strict_json(line))
    return rows


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline immutable Black Diamond daily audit")
    sub=p.add_subparsers(dest="mode",required=True)

    a=sub.add_parser("validate-payload")
    a.add_argument("payload")

    a=sub.add_parser("validate-ledger")
    a.add_argument("ledger")

    a=sub.add_parser("summary")
    a.add_argument("ledger")

    a=sub.add_parser("append")
    a.add_argument("ledger")
    a.add_argument("payload")
    a.add_argument("--record-id",required=True)
    a.add_argument("--expected-last-sha256",required=True)

    a=sub.add_parser("artifact-ref")
    a.add_argument("receipt")
    a.add_argument("--kind",required=True)

    args=p.parse_args(argv)
    try:
        if args.mode=="validate-payload":
            result={
                "mode":"IMMUTABLE_AUDIT_PAYLOAD_VALIDATION",
                "validated":True,
                "payload":validate_audit_payload(load(args.payload)),
            }
        elif args.mode=="validate-ledger":
            records=load_jsonl(args.ledger)
            result={
                "mode":"IMMUTABLE_AUDIT_LEDGER_VALIDATION",
                "validated":True,
                "record_count":len(records),
                "last_sha256":validate_daily_audit_chain(records),
            }
        elif args.mode=="summary":
            result=summarize_daily_audit(load_jsonl(args.ledger))
        elif args.mode=="append":
            digest=append_daily_audit_record(
                args.ledger,args.record_id,load(args.payload),
                expected_last_sha256=args.expected_last_sha256)
            result={
                "mode":"IMMUTABLE_AUDIT_APPEND",
                "record_id":args.record_id,
                "sha256":digest,
                "forecast_status":"HOLD",
                "wager_status":"NOT APPROVED",
            }
        else:
            result={
                "mode":"IMMUTABLE_AUDIT_ARTIFACT_REF",
                **artifact_ref_from_receipt(args.kind,load(args.receipt)),
            }
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
