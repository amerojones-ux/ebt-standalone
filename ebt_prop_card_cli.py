"""Render sanitized offline EBT.ai research cards only; never wager-approved."""
import argparse,json,sys
from pathlib import Path
from ebt_json import strict_json
from extensions.prop_card import render_research_card

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('input');parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:
        payload=strict_json(Path(args.input).read_text(encoding='utf-8'))
        html=render_research_card(payload)
        out=Path(args.output)
        if out.suffix.lower()!='.html':raise ValueError('output must be HTML')
        out.write_text(html,encoding='utf-8')
        print(json.dumps({'status':'CREATED_RESEARCH_CARD','file':str(out),'wager_status':'NOT APPROVED'}))
        return 0
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print(json.dumps({'status':'HOLD','error':str(exc)}));return 2
if __name__=='__main__':sys.exit(main())