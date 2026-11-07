"""Offline CLI for calibration certification review."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.calibration_certification import (
    assess_calibration_certification_review,
    candidate_calibration_uncertainty_diagnostic,
    verify_calibration_review_receipt,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(
        description="Offline calibration certification review")
    sub=p.add_subparsers(dest="mode",required=True)

    a=sub.add_parser("assess")
    a.add_argument("input")

    a=sub.add_parser("verify")
    a.add_argument("receipt")

    a=sub.add_parser("candidate")
    a.add_argument("input")

    args=p.parse_args(argv)
    try:
        if args.mode=="assess":
            row=load(args.input)
            required={
                "training","validation","scope","fit_at","assessed_at",
                "research_policy","acceptance_policy",
            }
            if not isinstance(row,dict) or set(row)!=required:
                raise ValueError("exact calibration review input schema required")
            result=assess_calibration_certification_review(
                row["training"],row["validation"],
                scope=row["scope"],fit_at=row["fit_at"],
                assessed_at=row["assessed_at"],
                research_policy=row["research_policy"],
                acceptance_policy=row["acceptance_policy"])
        elif args.mode=="verify":
            receipt=load(args.receipt)
            result={
                "mode":"CALIBRATION_REVIEW_RECEIPT_VERIFICATION",
                "verified":verify_calibration_review_receipt(receipt),
                "calibration_verified":False,
                "model_promotion_applied":False,
                "wager_status":"NOT APPROVED",
            }
        else:
            row=load(args.input)
            if not isinstance(row,dict) or set(row)!={
                "review_receipt","raw_probability","trials","seed"
            }:
                raise ValueError("exact candidate diagnostic schema required")
            result=candidate_calibration_uncertainty_diagnostic(
                row["review_receipt"],row["raw_probability"],
                trials=row["trials"],seed=row["seed"])
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),
            "calibration_verified":False,
            "wager_status":"NOT APPROVED",
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
