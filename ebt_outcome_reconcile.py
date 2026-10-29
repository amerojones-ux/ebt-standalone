"""Audit finalized prop labels without converting unknown outcomes into losses.

Caller-supplied records are not authenticated by this module.
"""
from ebt_certification import CertificationHold, timestamp

def reconcile_outcomes(predictions, finals, *, cutoff):
    if not isinstance(predictions,list) or not isinstance(finals,list):
        raise CertificationHold("prediction and final lists required")
    deadline=timestamp(cutoff)
    final_index={}
    for record in finals:
        if not isinstance(record,dict):
            raise CertificationHold("invalid final record")
        key=(record.get("event_id"),record.get("player_id"),record.get("market"))
        if any(not isinstance(v,str) or not v.strip() for v in key) or key in final_index:
            raise CertificationHold("missing or duplicate final identity")
        if record.get("status") not in {"final","postponed","cancelled","void"}:
            raise CertificationHold("unsupported final status")
        if timestamp(record.get("reported_at"))>deadline:
            raise CertificationHold("final after cutoff")
        if not isinstance(record.get("capture_id"),str) or not record["capture_id"].strip():
            raise CertificationHold("final evidence capture missing")
        final_index[key]=record
    results=[]
    seen=set()
    for prediction in predictions:
        if not isinstance(prediction,dict):
            raise CertificationHold("invalid prediction")
        key=(prediction.get("event_id"),prediction.get("player_id"),prediction.get("market"))
        if any(not isinstance(v,str) or not v.strip() for v in key) or key in seen:
            raise CertificationHold("duplicate or missing prediction identity")
        seen.add(key)
        threshold=prediction.get("threshold")
        if type(threshold) not in (int,float) or not (0<=threshold<float("inf")):
            raise CertificationHold("invalid threshold")
        if prediction.get("direction") not in {"over","under"}:
            raise CertificationHold("unsupported direction")
        if timestamp(prediction.get("issued_at"))>=timestamp(prediction.get("scheduled_start")):
            raise CertificationHold("prediction not pregame")
        record=final_index.get(key)
        if record is None:
            status="PENDING"
        elif record["status"]!="final":
            status="VOID"
        else:
            observed=record.get("value")
            if type(observed) not in (int,float) or not (0<=observed<float("inf")):
                raise CertificationHold("invalid final statistic")
            if observed==threshold:
                status="PUSH"
            elif (observed>threshold) == (prediction["direction"]=="over"):
                status="HIT"
            else:
                status="MISS"
        results.append({"event_id":key[0],"player_id":key[1],
                        "market":key[2],"result":status,
                        "final_capture_id":record["capture_id"] if record else None,
                        "outcome_truth_certified":False})
    return {"results":results,"all_finalized":all(x["result"]!="PENDING" for x in results),
            "independently_verified":False}
