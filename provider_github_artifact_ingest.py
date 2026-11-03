"""Preferred GitHub ingestion path requiring authorized + attested probe evidence."""
from provider_artifact_receipt_ingest import ingest_artifact_bytes
from provider_attestation_marker_artifact_ingest import (
    ingest_attestation_marker_artifact,
)
from provider_attestation_bundle_artifact_ingest import (
    ingest_attestation_bundle_artifact,
)
from provider_execution_intent_artifact_ingest import (
    ingest_execution_intent_artifact,
)
from provider_execution_intent_marker_artifact_ingest import (
    ingest_execution_intent_marker_artifact,
)
from provider_execution_intent_bundle_artifact_ingest import (
    ingest_execution_intent_bundle_artifact,
)
from provider_github_artifact_metadata import (
    build_trusted_binding,
    verify_downloaded_artifact,
)
from provider_receipt_review_candidate import bind_attestation_verification


_BINDING_KEYS=("expected_run_id","expected_commit","repository_id")


def _require_same_binding(label, candidate_binding, reference_binding):
    for key in _BINDING_KEYS:
        if candidate_binding[key]!=reference_binding[key]:
            raise ValueError(label+" GitHub provenance mismatch")


def ingest_github_artifact(
    receipt_metadata,
    receipt_zip_bytes,
    marker_metadata,
    marker_zip_bytes,
    bundle_metadata,
    bundle_zip_bytes,
    intent_metadata,
    intent_zip_bytes,
    intent_marker_metadata,
    intent_marker_zip_bytes,
    intent_bundle_metadata,
    intent_bundle_zip_bytes,
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
    _require_same_binding(
        "receipt/marker",
        marker_result["binding"],
        receipt_binding,
    )

    bundle_result=ingest_attestation_bundle_artifact(
        bundle_metadata,
        bundle_zip_bytes,
        provider=provider,
        trusted_now=trusted_now,
        expected_bundle_sha256=marker_result["attestation_bundle_sha256"],
    )
    _require_same_binding(
        "receipt/bundle",
        bundle_result["binding"],
        receipt_binding,
    )

    intent_result=ingest_execution_intent_artifact(
        intent_metadata,
        intent_zip_bytes,
        provider=provider,
        trusted_now=trusted_now,
    )
    _require_same_binding(
        "receipt/execution-intent",
        intent_result["binding"],
        receipt_binding,
    )

    intent_marker_result=ingest_execution_intent_marker_artifact(
        intent_marker_metadata,
        intent_marker_zip_bytes,
        provider=provider,
        trusted_now=trusted_now,
    )
    _require_same_binding(
        "receipt/execution-intent-marker",
        intent_marker_result["binding"],
        receipt_binding,
    )

    intent_bundle_result=ingest_execution_intent_bundle_artifact(
        intent_bundle_metadata,
        intent_bundle_zip_bytes,
        provider=provider,
        trusted_now=trusted_now,
        expected_bundle_sha256=intent_marker_result[
            "attestation_bundle_sha256"
        ],
    )
    _require_same_binding(
        "receipt/execution-intent-bundle",
        intent_bundle_result["binding"],
        receipt_binding,
    )

    if intent_result["intent_sha256"]!=intent_marker_result["intent_sha256"]:
        raise ValueError("execution intent checksum mismatch")
    if (
        intent_result["intent_file_sha256"]
        !=intent_marker_result["intent_file_sha256"]
    ):
        raise ValueError("execution intent file checksum mismatch")
    if (
        intent_result["request_plan_sha256"]
        !=intent_marker_result["request_plan_sha256"]
    ):
        raise ValueError("execution intent request-plan mismatch")
    if (
        intent_result["request_plan_sha256"]
        !=marker_result["request_plan_sha256"]
    ):
        raise ValueError("intent/receipt request-plan mismatch")
    if (
        intent_result["workflow_run_attempt"]!=1
        or intent_marker_result["workflow_run_attempt"]!=1
        or intent_result["workflow_run_attempt"]
            !=intent_marker_result["workflow_run_attempt"]
    ):
        raise ValueError("execution intent workflow attempt mismatch")
    if intent_result["actor"]!=intent_marker_result["actor"]:
        raise ValueError("execution intent actor mismatch")
    if intent_result["actor_id"]!=intent_marker_result["actor_id"]:
        raise ValueError("execution intent actor id mismatch")
    if intent_result["max_requests"]!=1 or intent_marker_result["max_requests"]!=1:
        raise ValueError("execution intent must authorize exactly one request")
    if (
        intent_marker_result["signer_workflow"]
        !=marker_result["signer_workflow"]
    ):
        raise ValueError("intent/receipt signer workflow mismatch")
    if (
        intent_bundle_result["bundle_file_sha256"]
        !=intent_marker_result["attestation_bundle_sha256"]
    ):
        raise ValueError("execution intent bundle checksum mismatch")

    receipt_result=ingest_artifact_bytes(
        receipt_zip_bytes,
        provider=provider,
        expected_run_id=receipt_binding["expected_run_id"],
        expected_commit=receipt_binding["expected_commit"],
    )
    if receipt_result["ingestion_status"]!="PENDING_ATTESTATION":
        raise ValueError("receipt ingestion state invalid")
    if (
        receipt_result["receipt_execution_intent_sha256"]
        !=intent_result["intent_sha256"]
    ):
        raise ValueError("receipt/execution-intent checksum binding mismatch")

    final_candidate=bind_attestation_verification(
        receipt_result["candidate"],
        marker_sha256=marker_result["marker_file_sha256"],
        request_plan_sha256=marker_result["request_plan_sha256"],
        source_repository=repository,
        attestation_id=marker_result["attestation_id"],
        attestation_url=marker_result["attestation_url"],
        signer_workflow=marker_result["signer_workflow"],
        execution_intent_sha256=intent_result["intent_sha256"],
        execution_intent_file_sha256=intent_result["intent_file_sha256"],
        execution_intent_marker_sha256=intent_marker_result["marker_file_sha256"],
        execution_intent_bundle_sha256=intent_bundle_result["bundle_file_sha256"],
        execution_intent_attestation_id=intent_marker_result["attestation_id"],
        execution_intent_attestation_url=intent_marker_result["attestation_url"],
        execution_actor=intent_result["actor"],
        execution_actor_id=intent_result["actor_id"],
        execution_max_requests=intent_result["max_requests"],
    )

    return {
        "status":"REVIEW_ONLY",
        "receipt_binding":receipt_binding,
        "receipt_zip_sha256":receipt_zip_sha256,
        "receipt_execution_intent_sha256":
            receipt_result["receipt_execution_intent_sha256"],
        "attestation_verification":marker_result,
        "attestation_bundle":bundle_result,
        "execution_intent":intent_result,
        "execution_intent_verification":intent_marker_result,
        "execution_intent_bundle":intent_bundle_result,
        "candidate":final_candidate,
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    }
