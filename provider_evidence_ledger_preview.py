"""Dry-run provider evidence-ledger preview from an attested review decision.

Never writes the real ledger or readiness config.
"""
import copy

from provider_attested_review_decision import verify_attested_review_decision
from provider_readiness_evidence_gate import validate_ledger

def build_ledger_preview(ledger, attested_review_decision, *, trusted_now):
    if not verify_attested_review_decision(attested_review_decision):
        raise ValueError("attested review decision verification failed")
    if attested_review_decision.get("decision")!="APPROVE":
        raise ValueError("only attested approved decisions can produce ledger previews")
    proposal=attested_review_decision.get("ledger_record_proposal")
    if not isinstance(proposal,dict):
        raise ValueError("attested ledger proposal missing")

    errors=validate_ledger(ledger,trusted_now=trusted_now)
    if errors:
        raise ValueError("current ledger invalid")

    subject=proposal["subject"]
    claim=proposal["claim"]
    updated=copy.deepcopy(ledger)

    target=None
    for entry in updated["providers"]:
        if entry.get("name")==subject:
            target=entry
            break
    if target is None:
        raise ValueError("provider not found in ledger")
    if target["evidence"].get(claim) is not None:
        raise ValueError("refusing to overwrite existing evidence")

    target["evidence"][claim]=copy.deepcopy(proposal)
    updated_errors=validate_ledger(updated,trusted_now=trusted_now)
    if updated_errors:
        raise ValueError("proposed ledger would be invalid")

    return {
        "preview_status":"VALID_MANUAL_PATCH_PREVIEW",
        "subject":subject,
        "claim":claim,
        "decision_sha256":attested_review_decision["decision_sha256"],
        "attested_decision_sha256":attested_review_decision[
            "attested_decision_sha256"
        ],
        "ledger_write_permitted":False,
        "readiness_write_permitted":False,
        "forecast_activation_permitted":False,
        "preview_ledger":updated,
    }
