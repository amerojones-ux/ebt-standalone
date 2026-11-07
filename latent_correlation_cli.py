"""Offline CLI for leakage-safe latent correlation estimation."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.latent_correlation_estimator import (
    build_joint_model_from_correlation_estimate,
    estimate_latent_correlation,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline latent-correlation research")
    sub=p.add_subparsers(dest="mode",required=True)

    a=sub.add_parser("estimate")
    a.add_argument("input")

    a=sub.add_parser("build-joint-model")
    a.add_argument("input")

    args=p.parse_args(argv)
    try:
        row=load(args.input)
        if not isinstance(row,dict):
            raise ValueError("input object required")
        if args.mode=="estimate":
            if set(row)!={"rows","variable_ids","forecast_cutoff","policy"}:
                raise ValueError("exact estimate schema required")
            result=estimate_latent_correlation(
                row["rows"],variable_ids=row["variable_ids"],
                forecast_cutoff=row["forecast_cutoff"],policy=row["policy"])
        else:
            if set(row)!={"marginals","correlation_receipt","model_locked_at"}:
                raise ValueError("exact build-joint-model schema required")
            result=build_joint_model_from_correlation_estimate(
                row["marginals"],row["correlation_receipt"],
                model_locked_at=row["model_locked_at"])
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
