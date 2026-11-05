"""Fail-closed forecast certification and immutable publication identity.

This module does not authorize wagers or claim empirical calibration.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from hashlib import sha256
import json

def _decimal(x):
    if isinstance(x,bool): raise ValueError("boolean is not a probability")
    try: value=Decimal(str(x))
    except (InvalidOperation,ValueError): raise ValueError("invalid decimal")
    if not value.is_finite(): raise ValueError("nonfinite decimal")
    return value

def _timestamp(value):
    if not isinstance(value,str): raise ValueError("timestamp required")
    try: dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: raise ValueError("invalid timestamp")
    if dt.tzinfo is None: raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)

@dataclass(frozen=True)
class CertificationEvidence:
    probability: object
    lower_bound: object
    central_cushion: object
    adverse_cushion: object
    source_verified: bool
    roster_verified: bool
    role_verified: bool
    calibrated_out_of_sample: bool
    scenario_verified: bool
    threshold_locked: bool
    injury_resolved: bool

def certify(e:CertificationEvidence,minimum_probability="0.87",minimum_lower="0.80"):
    p=_decimal(e.probability);lower=_decimal(e.lower_bound)
    central=_decimal(e.central_cushion);adverse=_decimal(e.adverse_cushion)
    if not (Decimal(0)<=lower<=p<=Decimal(1)): raise ValueError("invalid probability bounds")
    reasons=[]
    if p<_decimal(minimum_probability): reasons.append("probability below threshold")
    if lower<_decimal(minimum_lower): reasons.append("credible lower bound below threshold")
    if central<=0 or adverse<=0: reasons.append("nonpositive cushion")
    for field in ("source_verified","roster_verified","role_verified","calibrated_out_of_sample",
                  "scenario_verified","threshold_locked","injury_resolved"):
        if getattr(e,field) is not True: reasons.append(field+" missing")
    return {"status":"CERTIFIED_RESEARCH" if not reasons else "HOLD","reasons":reasons,
            "wager_status":"NOT_APPROVED"}

def lock_forecast(record):
    """Canonical publication identity. Persist externally to append-only storage."""
    required=("forecast_id","issued_at","event_at","player","market","threshold","model_version","probability")
    if any(key not in record or record[key] is None for key in required):
        raise ValueError("incomplete forecast")
    if _timestamp(record["issued_at"])>=_timestamp(record["event_at"]):
        raise ValueError("forecast not pregame")
    p=_decimal(record["probability"])
    if not Decimal(0)<=p<=Decimal(1): raise ValueError("probability")
    canonical=json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)
    return {"record":record,"sha256":sha256(canonical.encode()).hexdigest(),"locked":True}

def verify_locked_forecast(locked):
    if not locked.get("locked"): return False
    canonical=json.dumps(locked["record"],sort_keys=True,separators=(",",":"),allow_nan=False)
    return sha256(canonical.encode()).hexdigest()==locked["sha256"]
