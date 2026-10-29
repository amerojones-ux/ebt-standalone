"""Conservative evidence-readiness audit. No automatic release authority."""
from ebt_certification import CertificationHold

REQUIRED=("source_permissions","network_egress","provider_authenticity",
          "official_outcomes","holdout_calibration","human_signoff")

def evidence_readiness(checks):
    if not isinstance(checks,dict):
        raise CertificationHold("readiness checks must be a mapping")
    unknown=set(checks)-set(REQUIRED)
    if unknown:
        raise CertificationHold("unknown readiness check")
    findings={}
    for key in REQUIRED:
        entry=checks.get(key)
        if not isinstance(entry,dict):
            findings[key]="HOLD"
            continue
        evidence=entry.get("evidence_ids")
        reviewer=entry.get("reviewer")
        if (entry.get("status")=="REVIEWED"
            and isinstance(reviewer,str) and reviewer.strip()
            and isinstance(evidence,list) and evidence
            and all(isinstance(x,str) and x.strip() for x in evidence)):
            findings[key]="CLAIMED_REVIEWED"
        else:
            findings[key]="HOLD"
    return {"checks":findings,
            "missing_or_unreviewed":[k for k,v in findings.items() if v=="HOLD"],
            "externally_authenticated":False,
            "forecast_approved":False,
            "release_status":"HOLD"}
