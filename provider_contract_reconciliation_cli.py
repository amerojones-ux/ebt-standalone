"""CLI for seven-provider contract reconciliation."""
import sys
from provider_contract_reconciliation import summary, validate_configs

def main():
    errors=validate_configs()
    result=summary()
    print("PROVIDER_CONTRACT_RECONCILIATION:",result["status"])
    print("PROVIDER_COUNT:",result["provider_count"])
    print("ERROR_COUNT:",result["error_count"])
    for error in errors:
        print("CHECK:",error)
    print("No network requests or credentials accessed.")
    return 1 if errors else 0

if __name__=="__main__":
    sys.exit(main())
