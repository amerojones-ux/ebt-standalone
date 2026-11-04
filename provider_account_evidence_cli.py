"""CLI for redacted unresolved-provider account evidence."""
import json
from provider_account_evidence import gap_report

def main():
    result=gap_report()
    print("PROVIDER_ACCOUNT_EVIDENCE:",result["status"])
    for provider,gaps in result["gaps"].items():
        print(provider+":",str(len(gaps))+" gap(s)")
        for gap in gaps:
            print(" - "+gap)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="ACCOUNT_EVIDENCE_HOLD" else 1

if __name__=="__main__":
    raise SystemExit(main())
