"""CLI for the global provider activation gate."""
import argparse
import json
import sys
from provider_activation_gate import status, validate_config

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("config")
    args=parser.parse_args()
    with open(args.config, encoding="utf-8") as handle:
        config=json.load(handle)
    errors=validate_config(config)
    print("GLOBAL_PROVIDER_GATE:", status(config) if not errors else "INVALID_HOLD")
    for error in errors:
        print("CHECK:", error)
    print("No network requests or credentials accessed.")
    return 1 if errors else 0

if __name__=="__main__":
    sys.exit(main())
