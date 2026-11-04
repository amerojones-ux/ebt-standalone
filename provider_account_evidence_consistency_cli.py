"""CLI assertion for provider account/config consistency."""
import json
from provider_account_evidence_consistency import validate_consistency

def main():
    errors=validate_consistency()
    status="ACCOUNT_CONFIG_CONSISTENT" if not errors else "INVALID_HOLD"
    print("PROVIDER_ACCOUNT_CONFIG:",status)
    print(json.dumps({"status":status,"errors":errors},sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
