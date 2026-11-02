"""CLI for the global provider activation gate."""
import argparse
import json
import sys

from provider_activation_gate import status, validate_config
from provider_evidence_gate import evidence_supports_readiness

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument(
        "--evidence",
        default="config/provider_evidence.json",
        help="provider/model evidence ledger",
    )
    args=parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        config=json.load(handle)
    with open(args.evidence, encoding="utf-8") as handle:
        evidence=json.load(handle)

    config_errors=validate_config(config)
    evidence_errors=evidence_supports_readiness(config,evidence)
    all_errors=config_errors + evidence_errors
    evidence_ok=not evidence_errors

    print(
        "GLOBAL_PROVIDER_GATE:",
        status(config,evidence_ok=evidence_ok) if not config_errors else "INVALID_HOLD",
    )
    print("EVIDENCE_GATE:", "PASS" if evidence_ok else "HOLD")
    for error in all_errors:
        print("CHECK:",error)
    print("No network requests or credentials accessed.")
    return 1 if all_errors else 0

if __name__=="__main__":
    sys.exit(main())
