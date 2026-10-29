"""Validate captured source manifests offline; never equate metadata with truth."""
import hashlib,json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit
from ebt_validation import clock,number

KEY_FIELDS=('competition','event_id','subject_kind','subject_id','fact','metric','window','snapshot_kind')
FACTS={'schedule','roster','participation','lineup','team_stat','player_stat','market'}
CRITICAL={'schedule','roster','participation','lineup'}
KINDS={'official','teamrankings','secondary','market'}

def nonempty(value):return isinstance(value,str) and bool(value.strip())

def field_key(record):
    if not isinstance(record,dict) or any(not nonempty(record.get(k)) for k in KEY_FIELDS):
        raise ValueError('complete canonical field identity required')
    return tuple(record[k] for k in KEY_FIELDS)

def trusted_host(url,domains):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.username or parsed.password or not parsed.hostname:
        return False
    host=parsed.hostname.lower()
    return any(host==d or host.endswith('.'+d) for d in domains)

def validate_record(record,*,raw_root,cutoff,max_age_seconds,policy,_captures=None):
    """Returns (normalized, errors). Passes only capture/metadata checks."""
    try:
        key=field_key(record)
        if record.get('schema_version')!='1.0':raise ValueError('unsupported schema_version')
        if not nonempty(record.get('record_id')) or not nonempty(record.get('source_id')):raise ValueError('record/source IDs required')
        if record['fact'] not in FACTS or record['subject_kind'] not in ('event','team','player'):raise ValueError('unsupported fact or subject kind')
        if record['snapshot_kind'] not in ('LIVE','HISTORICAL'):raise ValueError('invalid snapshot kind')
        if record['fact'] in CRITICAL and record['snapshot_kind']!='LIVE':raise ValueError('historical evidence cannot clear current identity/status')
        kind=record.get('source_kind')
        if kind not in KINDS:raise ValueError('unsupported source kind')
        competition=policy['competitions'].get(record['competition'])
        if not competition:raise ValueError('competition policy unavailable')
        domains=competition.get(kind,[])
        if not domains or not trusted_host(record['source_url'],domains):raise ValueError('source domain not authorized for declared kind/competition')
        retrieved,effective,at=map(clock,(record['retrieved_at'],record['effective_at'],cutoff))
        if not effective<=retrieved<=at:raise ValueError('source timestamp order or cutoff violation')
        if record.get('published_at') is not None and not clock(record['published_at'])<=retrieved:raise ValueError('publication after retrieval')
        if record['snapshot_kind']=='LIVE' and (at-effective).total_seconds()>max_age_seconds:raise ValueError('stale effective source time')
        root=Path(raw_root).resolve(strict=True)
        raw_path=record['raw_path']
        if not nonempty(raw_path) or Path(raw_path).is_absolute():raise ValueError('relative raw capture path required')
        capture=(root/raw_path).resolve(strict=True)
        if not capture.is_relative_to(root) or not capture.is_file():raise ValueError('capture outside raw root or not a file')
        stamp=capture.stat()
        fingerprint=(stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns)
        cached=(_captures or {}).get(capture)
        if cached and cached[0]==fingerprint:digest=cached[1]
        else:
            digest=hashlib.sha256(capture.read_bytes()).hexdigest()
            after=capture.stat()
            if fingerprint!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('raw capture changed during hashing')
            if _captures is not None:_captures[capture]=(fingerprint,digest)
        if digest!=record['raw_sha256']:raise ValueError('raw capture SHA-256 mismatch')
        value=record.get('value')
        if record['fact'] in ('team_stat','player_stat'):
            value=str(number(value))
            if not nonempty(record.get('unit')) or type(record.get('sample_size')) is not int or record['sample_size']<=0:raise ValueError('numeric unit and positive sample_size required')
            start,end=clock(record['window_start']),clock(record['window_end'])
            if not start<=end<=effective:raise ValueError('stat window after source effective time')
        elif record['fact']=='participation':
            if record['subject_kind']!='player' or value not in ('ACTIVE','OUT','QUESTIONABLE','DOUBTFUL','PROBABLE','UNKNOWN'):raise ValueError('canonical player participation required')
        elif not nonempty(value):raise ValueError('nonempty categorical value required')
        return {**record,'value':value,'raw_sha256':digest,'validation':'CAPTURE_METADATA_VALID','field_key':list(key)},[]
    except (KeyError,TypeError,ValueError,AttributeError,ArithmeticError,OSError) as error:
        return None,[str(error)]

def ingest(records,requirements,*,raw_root,cutoff,max_age_seconds,policy):
    """Requirements declare coverage; no worldwide/slate completeness inferred."""
    if not isinstance(records,list) or not isinstance(requirements,list) or not requirements:raise ValueError('record array and nonempty requirement array required')
    if type(max_age_seconds) is not int or max_age_seconds<=0:raise ValueError('explicit positive freshness policy required')
    clock(cutoff)
    if not isinstance(policy,dict) or policy.get('version')!='1.0' or not isinstance(policy.get('competitions'),dict):raise ValueError('versioned competition/source policy required')
    for competition in policy['competitions'].values():
        if not isinstance(competition,dict):raise ValueError('competition policy must be an object')
        for kind,domains in competition.items():
            if kind not in KINDS or not isinstance(domains,list) or any(not nonempty(d) for d in domains):raise ValueError('invalid source-kind domain policy')
    required=[field_key(r) for r in requirements]
    if len(set(required))!=len(required):raise ValueError('duplicate required field')
    valid=[];rejected=[];seen={};groups=defaultdict(list);invalid_groups=set();captures={}
    for index,record in enumerate(records):
        normalized,errors=validate_record(record,raw_root=raw_root,cutoff=cutoff,max_age_seconds=max_age_seconds,policy=policy,_captures=captures)
        identity=record.get('record_id') if isinstance(record,dict) else None
        if nonempty(identity):
            if identity in seen:
                errors.append('duplicate record_id')
                if seen[identity] is not None:invalid_groups.add(seen[identity])
            else:
                try:seen[identity]=field_key(record)
                except ValueError:seen[identity]=None
        if errors:
            rejected.append({'index':index,'errors':errors})
            try:invalid_groups.add(field_key(record))
            except ValueError:pass
        else:
            valid.append(normalized);groups[tuple(normalized['field_key'])].append(normalized)
    output=[]
    for key in required:
        records_for_field=groups.get(key,[])
        latest={}
        for record in records_for_field:
            source=(record['source_kind'],urlsplit(record['source_url']).hostname,record['source_id']);prior=latest.get(source)
            stamp=clock(record['effective_at'])
            if prior is None or stamp>clock(prior[0]['effective_at']):latest[source]=[record]
            elif stamp==clock(prior[0]['effective_at']):latest[source].append(record)
        options=[r for values in latest.values() for r in values];fact=key[4]
        preferred='official' if fact in CRITICAL or fact=='player_stat' else 'teamrankings' if fact=='team_stat' else 'market'
        ranked=sorted(options,key=lambda r:(r['source_kind']!=preferred,-clock(r['effective_at']).timestamp(),r['record_id']))
        selected=ranked[0] if ranked else None
        conflict=len({signature(r) for r in options})>1
        reasons=[]
        if not selected:reasons.append('missing admissible evidence')
        if selected and selected['source_kind']!=preferred:reasons.append('preferred source authority missing')
        if conflict:reasons.append('unresolved source conflict')
        if key in invalid_groups:reasons.append('rejected evidence for this field requires review')
        if selected and fact=='participation' and selected['value']!='ACTIVE':reasons.append('participation not confirmed active')
        verdict='HOLD' if reasons else 'RESEARCH_INPUT'
        if fact=='participation' and any(r['source_kind']=='official' and r['value']=='OUT' for r in options):verdict='REJECT'
        output.append({'field_key':list(key),'verdict':verdict,'selected_record_id':selected['record_id'] if selected else None,'selected_value':selected['value'] if selected else None,'source_record_ids':[r['record_id'] for r in ranked],'conflict':conflict,'reasons':reasons})
    return {'schema_version':'1.0','mode':'OFFLINE_CAPTURE_REVIEW','policy_version':policy['version'],'cutoff':cutoff,'max_age_seconds':max_age_seconds,'required_fields':len(required),'valid_records':len(valid),'unique_valid_capture_hashes':len({r['raw_sha256'] for r in valid}),'rejected_records':rejected,'fields':output,'records':valid,'source_truth_verified':False,'forecast_approved':False,'coverage':'Only explicitly required fields; no slate completeness inferred.'}

def signature(record):
    if record['fact'] in ('team_stat','player_stat'):
        return (number(record['value']),record['unit'],record['sample_size'],clock(record['window_start']),clock(record['window_end']))
    return record['value']
