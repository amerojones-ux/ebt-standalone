"""Read-only consolidated safety status for the Black Diamond certification branch."""
from ebt_evidence_readiness import evidence_readiness
from ebt_release_manifest import audit_manifest
from ebt_certification import CertificationHold

def certification_summary(*, readiness_checks, release_manifest):
    readiness=evidence_readiness(readiness_checks)
    release=audit_manifest(release_manifest)
    return {
        "readiness":readiness,
        "release_manifest":release,
        "software_tests_substitute_for_external_evidence":False,
        "historical_truth_independently_verified":False,
        "live_forecast_approved":False,
        "production_deployment_approved":False,
        "status":"HOLD",
    }
