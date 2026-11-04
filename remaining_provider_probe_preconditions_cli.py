"""CLI assertion for remaining-provider precondition gates."""
import json
from remaining_provider_probe_preconditions import assess_all

def main():
    result=assess_all()
    print("REMAINING_PROVIDER_PROBE_PRECONDITIONS:",result["status"])
    for provider in result["providers"]:
        print(
            provider["provider"]+":",provider["status"],
            "| blockers="+str(len(provider["blockers"])),
            "| safety_errors="+str(len(provider["safety_errors"])),
        )
    print(json.dumps(result,sort_keys=True))
    if result["status"]=="BLOCKED_SAFE":
        print("No secret or provider network access permitted.")
        return 0
    return 1

if __name__=="__main__":
    raise SystemExit(main())
