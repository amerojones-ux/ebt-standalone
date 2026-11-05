"""Chronological calibration diagnostics and tamper-evident audit-chain verification.

Research only. Inputs must be independently certified and time-locked.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite

def _time(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None: raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)

def chronological_split(rows,train_fraction=.6,validation_fraction=.2):
    if not 0<train_fraction<1 or not 0<validation_fraction<1 or train_fraction+validation_fraction>=1:
        raise ValueError("invalid split")
    ordered=sorted(rows,key=lambda r:_time(r["issued_at"]))
    if len(ordered)<5: raise ValueError("insufficient history")
    n=len(ordered); a=max(1,int(n*train_fraction)); b=max(a+1,int(n*(train_fraction+validation_fraction)))
    if b>=n: raise ValueError("insufficient test set")
    for r in ordered:
        issued,event,settled=(_time(r[k]) for k in ("issued_at","event_at","settled_at"))
        if not issued<event<=settled: raise ValueError("invalid forecast chronology")
        if r["outcome"] not in (0,1) or not isinstance(r["probability"],(int,float)) or not isfinite(r["probability"]) or not 0<=r["probability"]<=1:
            raise ValueError("invalid outcome or probability")
    train,valid,test=ordered[:a],ordered[a:b],ordered[b:]
    # No training/validation outcome may be observed after the next phase begins.
    if max(_time(r["settled_at"]) for r in train)>=min(_time(r["issued_at"]) for r in valid):
        raise ValueError("train/validation settlement leakage")
    if max(_time(r["settled_at"]) for r in valid)>=min(_time(r["issued_at"]) for r in test):
        raise ValueError("validation/test settlement leakage")
    return train,valid,test

def calibration_bins(rows,edges=(0,.2,.4,.6,.8,1.)):
    if len(edges)<2 or edges[0]!=0 or edges[-1]!=1 or any(a>=b for a,b in zip(edges,edges[1:])):
        raise ValueError("invalid bins")
    groups=[[] for _ in range(len(edges)-1)]
    for r in rows:
        p=r["probability"]; y=r["outcome"]
        if not isinstance(p,(int,float)) or not isfinite(p) or not 0<=p<=1 or y not in (0,1):
            raise ValueError("invalid record")
        for i,(lo,hi) in enumerate(zip(edges,edges[1:])):
            if lo<=p<hi or (i==len(groups)-1 and p==hi):
                groups[i].append(r);break
    return [{"lower":lo,"upper":hi,"n":len(g),
             "mean_probability":sum(r["probability"] for r in g)/len(g) if g else None,
             "observed_rate":sum(r["outcome"] for r in g)/len(g) if g else None}
            for lo,hi,g in zip(edges,edges[1:],groups)]

def verify_audit_chain(records,genesis="genesis"):
    previous=genesis
    for record in records:
        payload=record["payload"]
        if payload["previous_hash"]!=previous: return False
        canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
        digest=sha256(canonical.encode()).hexdigest()
        if digest!=record["sha256"]: return False
        previous=digest
    return True
