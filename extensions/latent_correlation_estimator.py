"""Leakage-safe latent Gaussian-copula correlation estimation.

Uses complete-case historical events, midrank empirical normal scores, explicit
identity shrinkage, temporal drift windows, and Fisher-z uncertainty bands.
No sportsbook data are accepted. Cohort selection and source authentication are
external obligations.
"""
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from statistics import NormalDist
from typing import Any, Dict, Mapping, Sequence

from .underperformance import num

SHA_CHARS=set("0123456789abcdef")


def _clock(value: Any, field: str):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return dt.astimezone(timezone.utc)


def _sha(value: Any, field: str):
    if (
        not isinstance(value,str) or len(value)!=64
        or any(ch not in SHA_CHARS for ch in value)
    ):
        raise ValueError(f"{field} lowercase SHA-256 required")
    return value


def _policy(raw: Mapping[str,Any]):
    required={
        "min_complete_events","recent_window_events","shrinkage_to_identity",
        "max_allowed_abs_drift","max_pair_ci_width",
    }
    if not isinstance(raw,Mapping) or set(raw)!=required:
        raise ValueError("exact correlation policy schema required")
    min_events=raw["min_complete_events"]
    recent=raw["recent_window_events"]
    if type(min_events) is not int or min_events<4:
        raise ValueError("min_complete_events must be integer >=4")
    if type(recent) is not int or recent<4:
        raise ValueError("recent_window_events must be integer >=4")
    shrink=num(raw["shrinkage_to_identity"])
    drift=num(raw["max_allowed_abs_drift"])
    width=num(raw["max_pair_ci_width"])
    if not Decimal(0)<shrink<=Decimal(1):
        raise ValueError("shrinkage_to_identity must be in (0,1]")
    if not Decimal(0)<=drift<=Decimal(2):
        raise ValueError("max_allowed_abs_drift must be in [0,2]")
    if not Decimal(0)<width<=Decimal(2):
        raise ValueError("max_pair_ci_width must be in (0,2]")
    return {
        "min_complete_events":min_events,
        "recent_window_events":recent,
        "shrinkage_to_identity":shrink,
        "max_allowed_abs_drift":drift,
        "max_pair_ci_width":width,
    }


def _ingest(rows: Sequence[Mapping[str,Any]], variable_ids, cutoff):
    if not isinstance(rows,(list,tuple)) or not rows:
        raise ValueError("nonempty historical rows required")
    if (
        not isinstance(variable_ids,list) or len(variable_ids)<2
        or len(variable_ids)!=len(set(variable_ids))
        or any(not isinstance(x,str) or not x.strip() for x in variable_ids)
    ):
        raise ValueError("at least two unique variable IDs required")
    at=_clock(cutoff,"forecast_cutoff")
    required={
        "event_id","variable_id","value","event_time",
        "outcome_available_at","source_record_sha256",
    }
    events={}
    seen=set()
    for row in rows:
        if not isinstance(row,Mapping) or set(row)!=required:
            raise ValueError("exact correlation historical row schema required")
        event=row["event_id"]
        var=row["variable_id"]
        if not isinstance(event,str) or not event.strip():
            raise ValueError("event_id required")
        if var not in variable_ids:
            raise ValueError("historical row references unknown variable")
        key=(event,var)
        if key in seen:
            raise ValueError("duplicate event-variable observation")
        seen.add(key)
        value=num(row["value"])
        event_time=_clock(row["event_time"],f"{event}.{var}.event_time")
        available=_clock(row["outcome_available_at"],f"{event}.{var}.outcome_available_at")
        if not event_time<available<=at:
            raise ValueError("historical outcome timing violates forecast cutoff")
        source_hash=_sha(row["source_record_sha256"],f"{event}.{var}.source_record_sha256")
        e=events.setdefault(event,{
            "event_time":event_time,
            "outcome_available_at":available,
            "values":{},
            "source_hashes":{},
        })
        if e["event_time"]!=event_time:
            raise ValueError("event_time mismatch within historical event")
        e["outcome_available_at"]=max(e["outcome_available_at"],available)
        e["values"][var]=value
        e["source_hashes"][var]=source_hash
    complete=[]
    for event,payload in events.items():
        if set(payload["values"])==set(variable_ids):
            complete.append({
                "event_id":event,
                "event_time":payload["event_time"],
                "outcome_available_at":payload["outcome_available_at"],
                "values":payload["values"],
                "source_hashes":payload["source_hashes"],
            })
    complete.sort(key=lambda x:(x["event_time"],x["event_id"]))
    return events,complete,at


def _midrank_normal_scores(values):
    n=len(values)
    if n<2:
        raise ValueError("at least two observations required")
    indexed=sorted(enumerate(values),key=lambda x:(x[1],x[0]))
    ranks=[0.0]*n
    start=0
    while start<n:
        end=start
        while end+1<n and indexed[end+1][1]==indexed[start][1]:
            end+=1
        mid=((start+1)+(end+1))/2.0
        for pos in range(start,end+1):
            ranks[indexed[pos][0]]=mid
        start=end+1
    scores=[]
    normal=NormalDist()
    for rank in ranks:
        p=(rank-0.5)/n
        scores.append(normal.inv_cdf(p))
    mean=sum(scores)/n
    variance=sum((x-mean)**2 for x in scores)
    if variance<=1e-18:
        raise ValueError("zero-variance variable after rank transform")
    return scores


def _pearson(a,b):
    n=len(a)
    if n!=len(b) or n<2:
        raise ValueError("aligned correlation samples required")
    ma=sum(a)/n
    mb=sum(b)/n
    da=[x-ma for x in a]
    db=[x-mb for x in b]
    denom=math.sqrt(sum(x*x for x in da)*sum(y*y for y in db))
    if denom<=1e-18:
        raise ValueError("zero correlation denominator")
    value=sum(x*y for x,y in zip(da,db))/denom
    return max(-1.0,min(1.0,value))


def _matrix(complete,variable_ids):
    scores={}
    for var in variable_ids:
        scores[var]=_midrank_normal_scores([float(event["values"][var]) for event in complete])
    n=len(variable_ids)
    matrix=[[0.0]*n for _ in range(n)]
    for i,a in enumerate(variable_ids):
        matrix[i][i]=1.0
        for j in range(i+1,n):
            b=variable_ids[j]
            r=_pearson(scores[a],scores[b])
            matrix[i][j]=r
            matrix[j][i]=r
    return matrix


def _shrink(matrix,amount):
    lam=float(amount)
    n=len(matrix)
    return [
        [
            (1-lam)*matrix[i][j]+(lam if i==j else 0.0)
            for j in range(n)
        ]
        for i in range(n)
    ]


def _cholesky_positive_definite(matrix):
    n=len(matrix)
    out=[[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            v=matrix[i][j]-sum(out[i][k]*out[j][k] for k in range(j))
            if i==j:
                if v<=1e-12:
                    return False
                out[i][j]=math.sqrt(v)
            else:
                out[i][j]=v/out[j][j]
    return True


def _fisher_interval(r,n,zcrit=1.959963984540054):
    if n<=3:
        return (-1.0,1.0)
    bounded=max(-0.999999,min(0.999999,r))
    z=math.atanh(bounded)
    se=1/math.sqrt(n-3)
    return math.tanh(z-zcrit*se),math.tanh(z+zcrit*se)


def _pair_rows(matrix,variable_ids,n):
    rows=[]
    for i,a in enumerate(variable_ids):
        for j in range(i+1,len(variable_ids)):
            b=variable_ids[j]
            r=matrix[i][j]
            low,high=_fisher_interval(r,n)
            rows.append({
                "a":a,"b":b,"raw_normal_score_correlation":r,
                "fisher95_low":low,"fisher95_high":high,
                "fisher95_width":high-low,
            })
    return rows


def estimate_latent_correlation(
    rows: Sequence[Mapping[str,Any]],
    *,
    variable_ids: list,
    forecast_cutoff: str,
    policy: Mapping[str,Any],
) -> Dict[str,Any]:
    """Estimate a shrunk normal-score copula correlation matrix with drift gates."""
    p=_policy(policy)
    events,complete,at=_ingest(rows,variable_ids,forecast_cutoff)
    n=len(complete)
    coverage=n/len(events) if events else 0.0
    reasons=[]
    if n<p["min_complete_events"]:
        reasons.append("INSUFFICIENT_COMPLETE_EVENTS")
    if n<max(4,2*p["recent_window_events"]):
        reasons.append("INSUFFICIENT_DRIFT_WINDOWS")
    if reasons:
        return {
            "mode":"LEAKAGE_SAFE_LATENT_CORRELATION_ESTIMATOR",
            "status":"HOLD",
            "variable_ids":list(variable_ids),
            "historical_event_count":len(events),
            "complete_event_count":n,
            "complete_case_coverage":coverage,
            "reasons":reasons,
            "market_inputs_used":False,
            "calibration_verified":False,
            "forecast_status":"HOLD",
            "wager_status":"NOT APPROVED",
        }

    raw=_matrix(complete,variable_ids)
    shrunk=_shrink(raw,p["shrinkage_to_identity"])
    if not _cholesky_positive_definite(shrunk):
        reasons.append("SHRUNK_MATRIX_NOT_POSITIVE_DEFINITE")

    pair_rows=_pair_rows(raw,variable_ids,n)
    widest=max((row["fisher95_width"] for row in pair_rows),default=0.0)
    if widest>float(p["max_pair_ci_width"]):
        reasons.append("PAIRWISE_CORRELATION_UNCERTAINTY_TOO_WIDE")

    w=p["recent_window_events"]
    previous=complete[-2*w:-w]
    recent=complete[-w:]
    previous_matrix=_matrix(previous,variable_ids)
    recent_matrix=_matrix(recent,variable_ids)
    drifts=[]
    for i,a in enumerate(variable_ids):
        for j in range(i+1,len(variable_ids)):
            b=variable_ids[j]
            delta=recent_matrix[i][j]-previous_matrix[i][j]
            drifts.append({
                "a":a,"b":b,
                "previous_correlation":previous_matrix[i][j],
                "recent_correlation":recent_matrix[i][j],
                "absolute_drift":abs(delta),
            })
    max_drift=max((row["absolute_drift"] for row in drifts),default=0.0)
    if max_drift>float(p["max_allowed_abs_drift"]):
        reasons.append("CORRELATION_DRIFT_EXCEEDS_POLICY")

    canonical_rows=[
        {
            "event_id":event["event_id"],
            "event_time":event["event_time"].isoformat(),
            "outcome_available_at":event["outcome_available_at"].isoformat(),
            "values":{var:str(event["values"][var]) for var in variable_ids},
            "source_hashes":{var:event["source_hashes"][var] for var in variable_ids},
        }
        for event in complete
    ]
    input_sha=hashlib.sha256(
        json.dumps(
            {
                "rows":canonical_rows,
                "variable_ids":variable_ids,
                "forecast_cutoff":at.isoformat(),
                "policy":{k:str(v) for k,v in p.items()},
            },
            sort_keys=True,separators=(",",":"),allow_nan=False
        ).encode()
    ).hexdigest()
    matrix_sha=hashlib.sha256(
        json.dumps(
            {"variable_ids":variable_ids,"latent_correlation":shrunk},
            sort_keys=True,separators=(",",":"),allow_nan=False
        ).encode()
    ).hexdigest()
    status="RESEARCH_INPUT" if not reasons else "HOLD"
    return {
        "mode":"LEAKAGE_SAFE_LATENT_CORRELATION_ESTIMATOR",
        "status":status,
        "variable_ids":list(variable_ids),
        "forecast_cutoff":at.isoformat(),
        "historical_event_count":len(events),
        "complete_event_count":n,
        "complete_case_coverage":coverage,
        "shrinkage_to_identity":str(p["shrinkage_to_identity"]),
        "raw_normal_score_correlation":raw,
        "latent_correlation":shrunk,
        "positive_definite":_cholesky_positive_definite(shrunk),
        "pairwise_uncertainty":pair_rows,
        "widest_fisher95_interval":widest,
        "drift_previous_window_events":w,
        "drift_recent_window_events":w,
        "pairwise_temporal_drift":drifts,
        "max_absolute_temporal_drift":max_drift,
        "reasons":reasons,
        "input_sha256":input_sha,
        "matrix_sha256":matrix_sha,
        "market_inputs_used":False,
        "cohort_selection_external":True,
        "source_truth_verified_by_this_module":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }
