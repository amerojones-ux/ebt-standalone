"""Reconcile a complete official schedule snapshot against a previous snapshot.

This is a structural detector only. It cannot authenticate provider completeness.
"""
from ebt_certification import CertificationHold, timestamp

def reconcile_schedule(previous, current):
    for snapshot in (previous,current):
        if not isinstance(snapshot,dict) or snapshot.get("complete") is not True:
            raise CertificationHold("complete schedule snapshot required")
        if not isinstance(snapshot.get("capture_id"),str) or not snapshot["capture_id"].strip():
            raise CertificationHold("schedule capture missing")
        if not isinstance(snapshot.get("events"),list):
            raise CertificationHold("schedule events missing")
        ids=[]
        for event in snapshot["events"]:
            if not isinstance(event,dict) or not isinstance(event.get("event_id"),str) or not event["event_id"].strip():
                raise CertificationHold("invalid event ID")
            ids.append(event["event_id"])
        if len(ids)!=len(set(ids)):
            raise CertificationHold("duplicate event IDs")
    if previous["capture_id"]==current["capture_id"]:
        raise CertificationHold("distinct schedule captures required")
    if timestamp(previous.get("retrieved_at"))>=timestamp(current.get("retrieved_at")):
        raise CertificationHold("non-increasing schedule capture time")
    before={x["event_id"]:x for x in previous["events"]}
    after={x["event_id"]:x for x in current["events"]}
    removed=sorted(set(before)-set(after))
    added=sorted(set(after)-set(before))
    changed=sorted(k for k in set(before)&set(after) if before[k]!=after[k])
    return {"removed":removed,"added":added,"changed":changed,
            "requires_manual_review":bool(removed or added or changed),
            "schedule_truth_certified":False}
