"""CLI for creating a sanitized one-shot provider execution intent."""
import argparse
from datetime import datetime, timezone
import json

from provider_execution_intent import build_execution_intent

def main():
    parser=argparse.ArgumentParser()
    for name in (
        "provider","repository","workflow_run_id","source_commit",
        "source_ref","signer_workflow","actor","actor_id",
        "review_authorization","request_authorization",
    ):
        parser.add_argument("--"+name.replace("_","-"),dest=name,required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        result=build_execution_intent(
            provider=args.provider,
            repository=args.repository,
            workflow_run_id=args.workflow_run_id,
            source_commit=args.source_commit,
            source_ref=args.source_ref,
            signer_workflow=args.signer_workflow,
            actor=args.actor,
            actor_id=args.actor_id,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            review_authorization=args.review_authorization,
            request_authorization=args.request_authorization,
        )
        with open(args.output,"w",encoding="utf-8") as handle:
            json.dump(result,handle,indent=2,sort_keys=True)
            handle.write("\n")
    except (OSError,ValueError) as exc:
        print("PROVIDER_EXECUTION_INTENT: HOLD")
        print("CHECK:",str(exc))
        return 1
    print("PROVIDER_EXECUTION_INTENT: PREPARED_ONE_SHOT")
    print("INTENT_SHA256:",result["intent_sha256"])
    print("No provider secret or network request accessed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
