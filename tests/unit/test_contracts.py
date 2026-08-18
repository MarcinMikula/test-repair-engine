"""Unit tests for TestRepairEngine public contracts."""

import pytest
from pydantic import ValidationError

from test_repair_engine.contracts import (
    CartographerTraceability,
    LLMEvidence,
    LLMEvidenceOutcome,
    LocatorKind,
    ProjectReference,
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
    RepairRequest,
    RepairResult,
)
from test_repair_engine.contracts import TestOutcome as RepairTestOutcome

pytestmark = pytest.mark.unit


VALID_FINGERPRINT = "a" * 64


def _not_called_evidence(*, enabled: bool = False, eligible: bool = False) -> LLMEvidence:
    if enabled:
        return LLMEvidence(
            enabled=True,
            eligible=eligible,
            call_attempted=False,
            response_received=False,
            provider="ollama",
            model="qwen2.5-coder:7b",
            outcome=LLMEvidenceOutcome.NOT_CALLED,
        )
    return LLMEvidence(
        enabled=False,
        eligible=eligible,
        call_attempted=False,
        response_received=False,
        outcome=LLMEvidenceOutcome.NOT_CALLED,
    )


def test_repair_request_can_exist_without_cartographer() -> None:
    request = RepairRequest(
        action=RepairAction.FILL,
        original_locator="search-input",
    )

    assert request.locator_kind is LocatorKind.TEST_ID
    assert request.project_reference is None
    assert request.cartographer_traceability is None


def test_repair_request_can_carry_opaque_cartographer_references() -> None:
    request = RepairRequest(
        action=RepairAction.CLICK,
        original_locator="search-submit",
        project_reference=ProjectReference(
            project_profile_id="project-profile-main",
            project_profile_revision=2,
            configuration_fingerprint=VALID_FINGERPRINT,
        ),
        cartographer_traceability=CartographerTraceability(
            context_id="context-search",
            process_id="process-search",
            element_id="element-search-submit",
        ),
    )

    assert request.project_reference is not None
    assert request.project_reference.project_profile_revision == 2
    assert request.cartographer_traceability is not None
    assert request.cartographer_traceability.element_id == "element-search-submit"


def test_project_reference_requires_canonical_sha256_fingerprint() -> None:
    with pytest.raises(ValidationError, match="configuration_fingerprint"):
        ProjectReference(
            project_profile_id="project-profile-main",
            project_profile_revision=2,
            configuration_fingerprint="not-a-sha256",
        )


def test_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RepairRequest(
            action=RepairAction.CLICK,
            original_locator="search-submit",
            unexpected_field="must-not-be-accepted",
        )


def test_recovered_result_requires_replacement_locator() -> None:
    with pytest.raises(
        ValidationError,
        match="replacement_locator",
    ):
        RepairResult(
            outcome=RepairOutcome.RECOVERED,
            repair_method=RepairMethod.HEURISTIC,
            candidate_count=1,
        )


def test_recovered_result_requires_repair_method() -> None:
    with pytest.raises(
        ValidationError,
        match="repair_method",
    ):
        RepairResult(
            outcome=RepairOutcome.RECOVERED,
            replacement_locator="catalog-search-input",
            candidate_count=1,
        )


def test_recovered_result_requires_candidate_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match="at least one candidate",
    ):
        RepairResult(
            outcome=RepairOutcome.RECOVERED,
            replacement_locator="catalog-search-input",
            repair_method=RepairMethod.HEURISTIC,
        )


def test_failed_result_does_not_require_replacement() -> None:
    result = RepairResult(
        outcome=RepairOutcome.FAILED,
        reason="No suitable candidate found.",
    )

    assert result.replacement_locator is None
    assert result.repair_method is None


def test_llm_evidence_can_be_eligible_while_fallback_is_disabled() -> None:
    evidence = _not_called_evidence(enabled=False, eligible=True)

    assert evidence.enabled is False
    assert evidence.eligible is True
    assert evidence.call_attempted is False
    assert evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


def test_llm_evidence_call_requires_enabled_and_eligible() -> None:
    with pytest.raises(ValidationError, match="requires both enabled and eligible"):
        LLMEvidence(
            enabled=True,
            eligible=False,
            call_attempted=True,
            response_received=False,
            provider="ollama",
            model="qwen2.5-coder:7b",
            outcome=LLMEvidenceOutcome.TIMEOUT,
            latency_ms=100,
        )


def test_llm_evidence_requires_response_for_parsed_provider_outcomes() -> None:
    with pytest.raises(ValidationError, match="requires response_received=true"):
        LLMEvidence(
            enabled=True,
            eligible=True,
            call_attempted=True,
            response_received=False,
            provider="ollama",
            model="qwen2.5-coder:7b",
            outcome=LLMEvidenceOutcome.INVALID_SCHEMA,
            latency_ms=10,
        )


def test_llm_evidence_timeout_must_not_claim_response() -> None:
    with pytest.raises(ValidationError, match="requires response_received=false"):
        LLMEvidence(
            enabled=True,
            eligible=True,
            call_attempted=True,
            response_received=True,
            provider="ollama",
            model="qwen2.5-coder:7b",
            outcome=LLMEvidenceOutcome.TIMEOUT,
            latency_ms=10,
        )


def test_repair_record_separates_runtime_and_final_test_result() -> None:
    record = RepairRecord(
        run_id="run-001",
        test_node_id="tests/e2e/test_search.py::test_product_search",
        action=RepairAction.FILL,
        original_locator="search-input",
        replacement_locator="catalog-search-input",
        repair_method=RepairMethod.HEURISTIC,
        candidate_count=1,
        selected_score=0.91,
        runtime_result=RepairOutcome.RECOVERED,
        llm_evidence=_not_called_evidence(),
    )

    assert record.schema_version == "0.2"
    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.test_result is RepairTestOutcome.UNKNOWN


def test_v02_repair_record_requires_llm_evidence() -> None:
    with pytest.raises(ValidationError, match="v0.2 requires llm_evidence"):
        RepairRecord(
            run_id="run-001",
            action=RepairAction.FILL,
            original_locator="search-input",
            runtime_result=RepairOutcome.FAILED,
        )


def test_historical_v01_repair_record_preserves_absent_llm_evidence() -> None:
    record = RepairRecord(
        schema_version="0.1",
        run_id="run-historical",
        action=RepairAction.CLICK,
        original_locator="search-submit",
        runtime_result=RepairOutcome.FAILED,
    )

    assert record.schema_version == "0.1"
    assert record.llm_evidence is None


def test_v01_repair_record_rejects_backfilled_llm_evidence() -> None:
    with pytest.raises(ValidationError, match="v0.1 must not contain llm_evidence"):
        RepairRecord(
            schema_version="0.1",
            run_id="run-historical",
            action=RepairAction.CLICK,
            original_locator="search-submit",
            runtime_result=RepairOutcome.FAILED,
            llm_evidence=_not_called_evidence(),
        )


def test_recovered_record_requires_consistent_repair_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match="replacement_locator",
    ):
        RepairRecord(
            run_id="run-001",
            action=RepairAction.FILL,
            original_locator="search-input",
            repair_method=RepairMethod.HEURISTIC,
            candidate_count=1,
            runtime_result=RepairOutcome.RECOVERED,
            llm_evidence=_not_called_evidence(),
        )
