"""Offline streak intelligence from caller-supplied, final, identified CSV logs.

Approval manifests are operator assertions, NOT independent verification of rights,
source authenticity or downstream forecasting approval.
"""
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from .underperformance import num

REQUIRED = frozenset({'provider','license_reference','player_id','game_id',
                      'game_date','stat','value','participated','source_url',
                      'retrieved_at_utc','game_status'})


def utc(value):
    if not isinstance(value,str):
        raise ValueError('UTC timestamp required')
    try:
        x = datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:
        raise ValueError('invalid timestamp') from exc
    if x.tzinfo is None or x.utcoffset() is None or x.utcoffset().total_seconds()!=0:
        raise ValueError('UTC timestamp required')
    return x


def parse_manifest(path, asof):
    raw = Path(path).read_bytes()
    # Reject duplicate keys, including attempts to change an authorization claim.
    def pairs_unique(pairs):
        obj={}
        for k,v in pairs:
            if k in obj:
                raise ValueError('duplicate approval key')
            obj[k]=v
        return obj
    approval = json.loads(raw.decode('utf-8'),object_pairs_hook=pairs_unique)
    expected = ('provider','license_reference','approved_by','approved_at_utc',
                'valid_until_utc','permitted_use','contract_reference')
    if not isinstance(approval,dict) or any(not isinstance(approval.get(k),str) or not approval[k].strip() for k in expected):
        raise ValueError('incomplete operator rights manifest')
    if approval['permitted_use']!='sports_betting_analytics':
        raise ValueError('betting analytics use not asserted')
    if approval['provider'].strip().lower() in ('nba.com','nba stats','nba.com/stats'):
        raise ValueError('NBA stats bulk source disallowed without separate rights review')
    if not utc(approval['approved_at_utc']) <= asof <= utc(approval['valid_until_utc']):
        raise ValueError('operator approval time out of range')
    return approval, hashlib.sha256(raw).hexdigest()


def summarize_streak(rows, threshold, operator):
    """Supply NEWEST FIRST rows (value, participated, game_id) tuples."""
    if operator not in ('ge','gt','lt'):
        raise ValueError('ge/gt/lt operator required')
    t=num(threshold)
    seen=set(); eligible=[]
    for row in rows:
        game_id=row['game_id']
        if not isinstance(game_id,str) or not game_id or game_id in seen:
            raise ValueError('missing/duplicate game ID')
        seen.add(game_id)
        if row['participated'] is False:
            continue
        if row['participated'] is not True:
            raise ValueError('participation required')
        value=num(row['value'])
        hit = (value>=t if operator=='ge' else value>t if operator=='gt' else value<t)
        push = operator!='ge' and value==t
        eligible.append('PUSH' if push else 'HIT' if hit else 'MISS')
    run=0
    for status in eligible:
        if status!='HIT':
            break
        run+=1
    def window(n):
        sample=eligible[:n]; hits=sample.count('HIT'); pushes=sample.count('PUSH')
        return {'games':len(sample),'hits':hits,'misses':len(sample)-hits-pushes,
                'pushes':pushes,'hit_rate_descriptive':hits/len(sample) if sample else None}
    return {'consecutive_hits':run,'l5':window(5),'l10':window(10),
            'l20':window(20),'season':window(len(eligible)),
            'historical_only':True,'calibrated_next_event_probability':None}


def import_authorized_streak(csv_path, *, approval_path, player_id, stat,
                             threshold, operator, as_of_utc, cutoff_date=None):
    """Read complete local CSV. Fail closed on malformed/future/mixed-provider input.

    Does not contact feed, verify signatures, certify claimed provider rights,
    verify official game IDs, run simulations or approve a wager.
    """
    asof=utc(as_of_utc)
    if asof > datetime.now(timezone.utc):
        raise ValueError('future as-of time')
    approval, approval_sha=parse_manifest(approval_path,asof)
    cutoff=date.fromisoformat(cutoff_date) if cutoff_date else asof.date()
    if cutoff > asof.date():
        raise ValueError('future cutoff')
    raw=Path(csv_path).read_bytes()
    with Path(csv_path).open(newline='', encoding='utf-8-sig') as file:
        reader=csv.DictReader(file,strict=True)
        fields=reader.fieldnames
        if not fields or len(set(fields))!=len(fields) or not REQUIRED.issubset(fields):
            raise ValueError('invalid CSV schema/duplicate columns')
        rows=list(reader)
    if not rows:
        raise ValueError('empty feed')
    selected=[]; seen=set()
    for row in rows:
        if None in row or any(not isinstance(row.get(k),str) or not row[k].strip() for k in REQUIRED):
            raise ValueError('incomplete/malformed feed row')
        if row['provider'] != approval['provider'] or row['license_reference'] != approval['license_reference']:
            raise ValueError('provider/rights mismatch')
        if row['game_id'].strip().upper() in ('PENDING','UNKNOWN','UNRESOLVED'):
            raise ValueError('unresolved canonical game identity')
        if row['game_status'].upper() not in ('FINAL','CLOSED'):
            raise ValueError('unsettled game')
        played=row['participated'].lower()
        if played not in ('true','false'):
            raise ValueError('invalid participation')
        retrieved=utc(row['retrieved_at_utc'])
        game_date=date.fromisoformat(row['game_date'])
        if retrieved > asof or game_date > asof.date():
            raise ValueError('future/post-asof evidence')
        u=urlparse(row['source_url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password:
            raise ValueError('unsafe source URL')
        value=num(row['value'])
        if value < 0:
            raise ValueError('negative event statistic')
        if row['player_id']!=player_id or row['stat']!=stat or game_date>cutoff:
            continue
        key=(row['player_id'],row['stat'],row['game_id'])
        if key in seen:
            raise ValueError('duplicate player-game-stat')
        seen.add(key)
        selected.append({'game_id':row['game_id'],'date':game_date.isoformat(),
                         'value':str(value),'participated':played=='true'})
    if not selected:
        raise ValueError('no matching rows')
    selected.sort(key=lambda r:(r['date'],r['game_id']),reverse=True)
    result=summarize_streak(selected,threshold,operator)
    result.update({'mode':'OFFLINE_AUTHORIZED_FEED_STREAK_RESEARCH',
                   'forecast_status':'HOLD','wager_status':'NOT APPROVED',
                   'source_truth_verified':False,'rights_independently_verified':False,
                   'simulations':'NOT RUN',
                   'provenance':{'csv_sha256':hashlib.sha256(raw).hexdigest(),
                                 'manifest_sha256':approval_sha,'provider':approval['provider'],
                                 'player_id':player_id,'stat':stat,'rows_used':len(selected),
                                 'as_of_utc':as_of_utc,'operator':operator,
                                 'threshold':str(num(threshold)),
                                 'rights_status':'OPERATOR_ATTESTED_NOT_INDEPENDENTLY_VERIFIED'}})
    return result