"""CLI for prepared provider probe readiness registry."""
import json
from provider_probe_readiness_registry import assess_all

def main():
    result=assess_all()
    print("PROBE_READINESS_REGISTRY:",result["status"])
    print("PROBE_COUNT:",result["probe_count"])
    for probe in result["probes"]:
        print(
            "PROBE:",
            probe["provider"],
            probe["status"],
            "MANUAL_DISPATCH_REQUIRED="+str(probe["manual_dispatch_required"]),
            "EXECUTION_CLAIMED="+str(probe["execution_claimed"]),
        )
        for error in probe["errors"]:
            print("CHECK:",probe["provider"],error)
    print("No provider request, secret read, or execution claim performed.")
    return 0 if result["status"]=="PREPARED_DEFAULT_DENY" else 1

if __name__=="__main__":
    raise SystemExit(main())
