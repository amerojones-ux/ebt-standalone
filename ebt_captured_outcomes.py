"""Verify outcome capture bytes before classifying official final-stat records.

Synthetic tests only; host allowlisting and hashing do not establish truth.
"""
import json
from pathlib import Path
from ebt_capture_index import verify_capture
from ebt_certification import CertificationHold
from ebt_outcome_reconcile import reconcile_outcomes

def reconcile_captured_outcomes(predictions, finals, index, raw_root, *,
                                cutoff, allowed_hosts):
    official_hosts={"official.nba.com","nba.com"}
    checked=[]
    for record in finals:
        if not isinstance(record,dict):
            raise CertificationHold("invalid final record")
        cid=record.get("capture_id")
        capture=verify_capture(cid,index,raw_root,cutoff=cutoff,
                               allowed_hosts=allowed_hosts)
        if capture["host"] not in official_hosts:
            raise CertificationHold("final capture not from approved official host")
        entry=index[cid]
        raw=(Path(raw_root).resolve()/entry["raw_path"]).resolve()
        try:
            payload=json.loads(raw.read_text(encoding="utf-8"))
        except (UnicodeError,ValueError) as exc:
            raise CertificationHold("invalid final capture JSON") from exc
        if not isinstance(payload,dict) or payload.get("event_id")!=record.get("event_id") or payload.get("player_id")!=record.get("player_id") or payload.get("market")!=record.get("market") or payload.get("status")!=record.get("status"):
            raise CertificationHold("final capture content mismatch")
        if record.get("status")=="final" and (type(payload.get("value")) not in (int,float) or payload["value"]!=record.get("value")):
            raise CertificationHold("final statistic mismatch")
        if payload.get("reported_at")!=record.get("reported_at"):
            raise CertificationHold("final timestamp mismatch")
        checked.append(cid)
    result=reconcile_outcomes(predictions,finals,cutoff=cutoff)
    result["capture_content_matched"]=True
    result["capture_count"]=len(checked)
    result["independently_verified"]=False
    return result
