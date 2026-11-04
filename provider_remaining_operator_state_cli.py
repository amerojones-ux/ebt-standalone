"""CLI for deterministic remaining-provider operator state."""
import argparse
import json

from provider_remaining_operator_state import assess_remaining_provider_state

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output")
    args=parser.parse_args()
    result=assess_remaining_provider_state()
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.output:
        with open(args.output,"w",encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text,end="")
    if result["status"]=="INVALID_HOLD":
        raise SystemExit(2)

if __name__=="__main__":
    main()
