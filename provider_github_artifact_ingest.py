"""Preferred ingestion path using GitHub artifact metadata plus ZIP bytes."""
from provider_artifact_receipt_ingest import ingest_artifact_bytes
from provider_github_artifact_metadata import build_trusted_binding

def ingest_github_artifact(metadata, zip_bytes, *, provider, trusted_now):
    binding=build_trusted_binding(
        metadata,provider=provider,trusted_now=trusted_now
    )
    result=ingest_artifact_bytes(
        zip_bytes,
        provider=provider,
        expected_run_id=binding["expected_run_id"],
        expected_commit=binding["expected_commit"],
    )
    return {
        "status":"REVIEW_ONLY",
        "binding":binding,
        "receipt_ingestion":result,
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    }
