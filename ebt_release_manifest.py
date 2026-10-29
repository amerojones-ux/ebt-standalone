"""Reproducible certification manifest inspection; no automatic forecast release."""
import hashlib
import json
from ebt_certification import CertificationHold

def canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def audit_manifest(manifest):
    if not isinstance(manifest,dict) or manifest.get("schema_version")!="1.0":
        raise CertificationHold("invalid manifest schema")
    required=("source_policy","identity","availability","schedule",
              "history","calibration","operational_signoff")
    gates=manifest.get("gates")
    if not isinstance(gates,dict) or any(k not in gates for k in required):
        raise CertificationHold("incomplete release manifest")
    for name in required:
        entry=gates[name]
        if not isinstance(entry,dict) or entry.get("status") not in {"HOLD","REVIEWED"}:
            raise CertificationHold("invalid gate status: "+name)
        if entry["status"]=="REVIEWED":
            if not isinstance(entry.get("reviewer"),str) or not entry["reviewer"].strip():
                raise CertificationHold("missing reviewer: "+name)
            captures=entry.get("evidence_ids")
            if not isinstance(captures,list) or not captures or any(not isinstance(x,str) or not x.strip() for x in captures):
                raise CertificationHold("missing reviewed evidence: "+name)
    complete=all(gates[k]["status"]=="REVIEWED" for k in required)
    digest=hashlib.sha256(canonical_json(manifest)).hexdigest()
    return {"manifest_sha256":digest,"all_gates_reviewed":complete,
            "status":"MANUAL_RELEASE_REVIEW_REQUIRED" if complete else "HOLD",
            "forecast_approved":False}
