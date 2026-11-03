"""Preferred GitHub ingestion path requiring receipt + verified attestation marker."""
from provider_artifact_receipt_ingest import ingest_artifact_bytes
from provider_attestation_marker_artifact_ingest import (
    ingest_attestation_marker_artifact,
)
from provider_attestation_bundle_artifact_ingest import (
    ingest_attestation_bundle_artifact,
)
from provider_github_artifact_metadata import (
    build_trusted_binding,
    verify_downloaded_artifact,
)
from provider_receipt_review_candidate import bind_attestation_verification

def ingest_github_artifact(
    receipt_metadata,
    receipt_zip_bytes,
    marker_metadata,
    marker_zip_bytes,
    bundle_metadata,
    bundle_zip_bytes,
    *,
    provider,
    repository,
    trusted_now,
):
    receipt_binding=build_trusted_binding(
        receipt_metadata,provider=provider,trusted_now=trusted_now
    )
    receipt_zip_sha256=verify_downloaded_artifact(
        receipt_binding,receipt_zip_bytes
    )
    marker_result=ingest_attestation_marker_artifact(
        marker_metadata,
        marker_zip_bytes,
        provider=provider,
        repository=repository,
        trusted_now=trusted_now,
    )

    marker_binding=marker_result["binding"]
    bundle_result=ingest_attestation_bundle_artifact(
        bundle_metadata,
        bundle_zip_bytes,
        provider=provider,
        trusted_now=trusted_now,
        expected_bundle_sha256=marker_result["attestation_bundle_sha256"],
    )
    bundle_binding=bundle_result["binding"]
    for key in ("expected_run_id","expected_commit","repository_id"):
        if marker_binding[key]!=receipt_binding[key]:
            raise ValueError("receipt/marker GitHub provenance mismatch")
        if bundle_binding[key]!=receipt_binding[key]:
            raise ValueError("receipt/bundle GitHub provenance mismatch")

    receipt_result=ingest_artifact_bytes(
        receipt_zip_bytes,
        provider=provider,
        expected_run_id=receipt_binding["expected_run_id"],
        expected_commit=receipt_binding["expected_commit"],
    )
    if receipt_result["ingestion_status"]!="PENDING_ATTESTATION":
        raise ValueError("receipt ingestion state invalid")

    final_candidate=bind_attestation_verification(
        receipt_result["candidate"],
        marker_sha256=marker_result["marker_file_sha256"],
        request_plan_sha256=marker_result["request_plan_sha256"],
        source_repository=repository,
        attestation_id=marker_result["attestation_id"],
        attestation_url=marker_result["attestation_url"],
        signer_workflow=marker_result["signer_workflow"],
    )

    return {
        "status":"REVIEW_ONLY",
        "receipt_binding":receipt_binding,
        "receipt_zip_sha256":receipt_zip_sha256,
        "attestation_verification":marker_result,
        "attestation_bundle":bundle_result,
        "candidate":final_candidate,
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    }
