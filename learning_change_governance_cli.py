"""Offline CLI for V7 learning-change governance."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.learning_change_governance import (
    assess_learning_change_review,
    verify_learning_review_receipt,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(
        description="Offline V7 model-learning change review gate")
    sub=p.add_subparsers(dest="mode",required=True)

    a=sub.add_parser("assess")
    a.add_argument("input")

    a=sub.add_parser("verify")
    a.add_argument("receipt")

    args=p.parse_args(argv)
    try:
        if args.mode=="assess":
            result=assess_learning_change_review(load(args.input))
        else:
            receipt=load(args.receipt)
            result={
                "mode":"V7_LEARNING_CHANGE_RECEIPT_VERIFICATION",
                "verified":verify_learning_review_receipt(receipt),
                "weight_change_applied":False,
                "model_promotion_applied":False,
                "wager_status":"NOT APPROVED",
            }
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD",
            "error":str(exc),
            "weight_change_applied":False,
            "wager_status":"NOT APPROVED",
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
