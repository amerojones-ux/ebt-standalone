"""Static electric sports-research prop card (untrusted fields escaped).

A visual does not grant live evidence, calibrated probabilities or wager approval.
"""
from html import escape
from .underperformance import num

REQUIRED=('subject','opponent','event','event_ct','market','comparator','threshold',
          'p50','adverse_p50','model_version','source_status')
ALLOWED_SOURCE={'FOUND','N/A','BLOCKED','STALE','CONFLICTING','ADAPTER UNAVAILABLE','PENDING'}

def render_research_card(card):
    if not isinstance(card,dict) or any(key not in card for key in REQUIRED):
        raise ValueError('complete research identity and projection fields required')
    if card['comparator'] not in ('GE','GT','LT'):
        raise ValueError('explicit settlement comparator required')
    if card['source_status'] not in ALLOWED_SOURCE:
        raise ValueError('explicit source coverage status required')
    for key in ('subject','opponent','event','event_ct','market','model_version'):
        if not isinstance(card[key],str) or not card[key].strip():
            raise ValueError('nonempty identity and model version required')
    threshold=num(card['threshold']);central=num(card['p50']);adverse=num(card['adverse_p50'])
    sign=1 if card['comparator'] in ('GE','GT') else -1
    central_units=sign*(central-threshold);adverse_units=sign*(adverse-threshold)
    central_pct='N/A' if threshold==0 else str((100*central_units/abs(threshold)).quantize(num('.01')))+'%'
    def text(value):return escape(str(value),quote=True)
    def field(title,value):
        return f'<div class="metric"><span class="label">{text(title)}</span><strong>{text(value)}</strong></div>'
    probability=card.get('modeled_probability')
    if probability is None:
        probability_label='PENDING (no calibrated probability)'
    else:
        p=num(probability)
        if not 0<=p<=1:raise ValueError('probability range')
        probability_label=f'{(p*100).quantize(num(".01"))}% MODELED / UNCALIBRATED'
    mc=card.get('simulation_status','NOT RUN')
    if mc!='NOT RUN':
        raise ValueError('this presentation adapter cannot verify MC logs; render NOT RUN')
    metrics=''.join((field('P50 projection',central),field('Adverse P50',adverse),
                     field('Threshold',str(threshold)+' ('+card['comparator']+')'),
                     field('Central cushion',str(central_units)+' / '+central_pct),
                     field('Adverse cushion',adverse_units),field('Probability',probability_label),
                     field('Source status',card['source_status']),field('MC runs','NOT RUN')))
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EBT.ai Research Prop Card</title><style>
:root{color-scheme:dark}body{background:#070b12;color:#f4f7fd;font:16px system-ui,sans-serif;margin:0;padding:2rem}
.card{margin:auto;max-width:850px;background:linear-gradient(160deg,#122334 0%,#060c15 80%);border:2px solid #d8ae45;
border-radius:20px;padding:clamp(1rem,4vw,2.1rem);box-shadow:0 0 25px #b78a3133,inset 0 0 0 4px #101923}
.brand{font-size:.9rem;letter-spacing:.19em;color:#eccc69;font-weight:800}.headline{font-weight:850;font-size:clamp(1.4rem,4vw,2.4rem);
color:#5ff6ff;margin:.45rem 0}.subtitle{color:#b9ccd7}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:1.6rem 0}
.metric{background:#111d2c;border:1px solid #35536a;border-radius:10px;padding:13px;min-width:0;overflow-wrap:anywhere}
.label{display:block;color:#90b8c6;font-size:.77rem;letter-spacing:.08em;text-transform:uppercase;margin-bottom:.45rem}
.metric strong{font-size:1.05rem;color:#fff}.hold{color:#ffdb8c;border:1px solid #a77635;padding:12px;border-radius:8px}
footer{color:#acbccb;font-size:.8rem;line-height:1.6}</style></head><body><article class="card">
<div class="brand">◆ EBT.AI · BLACK DIAMOND OS</div><h1 class="headline">''' + text(card['subject']) + ' vs '+text(card['opponent']) + '''</h1>
<div class="subtitle">''' + text(card['event']) + ' • '+text(card['event_ct'])+' CT • '+text(card['market']) + '''</div>
<div class="grid">''' + metrics + '''</div><p class="hold"><strong>FORECAST: HOLD</strong> · <strong>WAGER: NOT APPROVED</strong></p>
<footer>Model: ''' + text(card['model_version']) + '''. Threshold settlement semantics and source freshness must be verified.
Graphics are not evidence. Exact live bookmaker price, independent calibration, three retained >=100k simulation results,
and final event/role validation are required for any separate approval decision.</footer></article></body></html>'''