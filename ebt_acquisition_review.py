"""Review external acquisition attestations without pretending to authenticate them.

An attestation must be checked by an authorized acquisition system or reviewer.
"""
from ebt_certification import CertificationHold, timestamp
from ebt_capture_index import verify_capture

def acquisition_review(capture_id,index,raw_root,*,cutoff,allowed_hosts):
    checked=verify_capture(capture_id,index,raw_root,cutoff=cutoff,allowed_hosts=allowed_hosts)
    entry=index[capture_id]
    att=entry.get("acquisition")
    if not isinstance(att,dict):
        raise CertificationHold("acquisition attestation missing")
    if att.get("method") not in {"authorized_api","permitted_public_endpoint"}:
        raise CertificationHold("unsupported acquisition method")
    if not isinstance(att.get("collector_version"),str) or not att["collector_version"].strip():
        raise CertificationHold("collector version missing")
    if not isinstance(att.get("request_id"),str) or not att["request_id"].strip():
        raise CertificationHold("request identifier missing")
    if att.get("tls_verified") is not True:
        raise CertificationHold("TLS verification not attested")
    if att.get("http_status")!=200 or type(att.get("http_status")) is not int:
        raise CertificationHold("unsuccessful HTTP acquisition")
    if timestamp(att.get("completed_at"))>timestamp(entry["retrieved_at"]):
        raise CertificationHold("acquisition completion after capture time")
    return {"capture_integrity_verified":checked["integrity_verified"],
            "attestation_structurally_valid":True,
            "provider_authenticity_verified":False,
            "manual_acquisition_review_required":True}
