"""Synthetic default-deny fixtures independent of operational evidence."""
from provider_readiness_evidence_gate import PROVIDERS, PROVIDER_CLAIMS, MODEL_CLAIMS

def ledger():
    return {"schema_version":5,"providers":[{"name":n,"evidence":{c:None for c in PROVIDER_CLAIMS}} for n in sorted(PROVIDERS)],"model_gates":{c:None for c in MODEL_CLAIMS}}

def readiness():
    return {"forecast_enabled":False,"network_autorun_enabled":False,"required_providers":[],"providers":[{"name":n,"role":"primary_stats","contract_ready":True,**{c:False for c in PROVIDER_CLAIMS}} for n in sorted(PROVIDERS)],"model_gates":{c:False for c in MODEL_CLAIMS}}
