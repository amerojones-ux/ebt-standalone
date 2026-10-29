"""Conservative out-of-sample probability calibration diagnostics.

Accepts independently supplied historical labels; never certifies those labels.
"""
import math
from ebt_certification import CertificationHold, timestamp

def calibration_report(rows, *, cutoff, min_samples=100):
    if not isinstance(rows,list) or not rows:
        raise CertificationHold("no evaluation rows")
    if type(min_samples) is not int or min_samples < 1:
        raise CertificationHold("invalid sample requirement")
    deadline=timestamp(cutoff)
    seen=set()
    errors=[]
    bins={}
    for row in rows:
        if not isinstance(row,dict) or row.get("certified") is not True:
            raise CertificationHold("uncertified evaluation row")
        key=(row.get("event_id"),row.get("player_id"),row.get("market"),row.get("threshold"))
        if any(x is None or x=="" for x in key) or key in seen:
            raise CertificationHold("missing or duplicate evaluation key")
        seen.add(key)
        p=row.get("predicted_probability")
        outcome=row.get("hit")
        if type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1 or type(outcome) is not bool:
            raise CertificationHold("invalid probability or outcome")
        issued=timestamp(row.get("issued_at"))
        start=timestamp(row.get("scheduled_start"))
        finalized=timestamp(row.get("finalized_at"))
        if not issued<start<=finalized<=deadline:
            raise CertificationHold("prediction leakage or unfinalized outcome")
        errors.append((p-int(outcome))**2)
        bucket=min(int(p*10),9)
        acc=bins.setdefault(bucket,{"count":0,"predicted_sum":0.0,"hits":0})
        acc["count"]+=1
        acc["predicted_sum"]+=p
        acc["hits"]+=int(outcome)
    n=len(rows)
    summary={str(k):{"count":v["count"],
        "mean_prediction":round(v["predicted_sum"]/v["count"],6),
        "observed_frequency":round(v["hits"]/v["count"],6)}
        for k,v in sorted(bins.items())}
    return {"n":n,"brier_score":round(sum(errors)/n,8),
            "bins":summary,"minimum_sample_met":n>=min_samples,
            "calibration_approved":False,
            "outcome_truth_independently_verified":False}
