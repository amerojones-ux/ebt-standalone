"""Cross-reference evidence gates with verified capture bytes and provenance.

Integrity is necessary, not sufficient, for truth or release certification.
"""
from ebt_capture_index import verify_capture, corroborate_distinct_sources
from ebt_certification import (CertificationHold, identity_check,
                               availability_check, historical_certification)

def verify_identity_evidence(event, player, index, raw_root, *, cutoff, allowed_hosts):
    identity_check(event, player)
    captures = corroborate_distinct_sources(
        player["corroboration_capture_ids"], index, raw_root,
        cutoff=cutoff, allowed_hosts=allowed_hosts)
    return {"identity_structurally_valid":True,
            "capture_integrity_verified":captures["integrity_verified"],
            "identity_truth_certified":False}

def verify_availability_evidence(report, index, raw_root, *, cutoff, max_age_seconds, allowed_hosts):
    availability_check(report, cutoff=cutoff, max_age_seconds=max_age_seconds)
    capture = verify_capture(report["capture_id"],index,raw_root,
                             cutoff=cutoff,allowed_hosts=allowed_hosts)
    if capture["host"] not in {"official.nba.com","nba.com"}:
        raise CertificationHold("availability capture must use approved official host")
    if report["retrieved_at"] != index[report["capture_id"]].get("retrieved_at"):
        raise CertificationHold("availability capture timestamp mismatch")
    return {"availability_structurally_valid":True,
            "capture_integrity_verified":True,"availability_truth_certified":False}

def verify_historical_evidence(record, index, raw_root, *, cutoff, allowed_hosts):
    historical_certification(record)
    if record["outcome_capture_id"] in record["source_capture_ids"]:
        raise CertificationHold("outcome capture cannot be pregame feature capture")
    for cid in record["source_capture_ids"]:
        verify_capture(cid,index,raw_root,cutoff=record["prediction_created_at"],
                       allowed_hosts=allowed_hosts)
    outcome = verify_capture(record["outcome_capture_id"],index,raw_root,
                             cutoff=cutoff,allowed_hosts=allowed_hosts)
    if outcome["host"] not in {"official.nba.com","nba.com"}:
        raise CertificationHold("outcome capture must use approved official host")
    if record["outcome_final_at"] > cutoff:
        raise CertificationHold("outcome final after review cutoff")
    return {"history_temporally_valid":True,
            "capture_integrity_verified":True,"historical_truth_certified":False}
