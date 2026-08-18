"""Unit tests for pytest-correlated runtime repair evidence."""

from pathlib import Path

import pytest

from test_repair_engine.contracts import (
    LLMEvidenceOutcome,
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.contracts import TestOutcome as RepairTestOutcome
from test_repair_engine.recording import load_repair_record
from test_repair_engine.runtime import (
    completed_llm_evidence,
    configure_runtime,
    current_llm_configuration,
    current_llm_evidence,
    current_run_id,
    finalize_test,
    llm_fallback_enabled,
    mark_test_failed,
    register_repair,
    reset_runtime,
    set_current_test_node,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    reset_runtime()
    yield
    reset_runtime()


def test_finalize_test_marks_repair_passed_and_persists_it(tmp_path: Path) -> None:
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    register_repair(
        RepairRecord(
            run_id=current_run_id(),
            test_node_id=node_id,
            action=RepairAction.FILL,
            original_locator="search-input",
            replacement_locator="catalog-search-input",
            repair_method=RepairMethod.HEURISTIC,
            candidate_count=1,
            selected_score=0.91,
            runtime_result=RepairOutcome.RECOVERED,
            llm_evidence=current_llm_evidence(eligible=False),
        )
    )

    written = finalize_test(node_id)

    assert len(written) == 1
    loaded = load_repair_record(written[0])
    assert loaded.runtime_result is RepairOutcome.RECOVERED
    assert loaded.test_result is RepairTestOutcome.PASSED


def test_finalize_test_marks_repair_failed_when_any_pytest_phase_failed(tmp_path: Path) -> None:
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    register_repair(
        RepairRecord(
            run_id=current_run_id(),
            test_node_id=node_id,
            action=RepairAction.FILL,
            original_locator="search-input",
            replacement_locator="catalog-search-input",
            repair_method=RepairMethod.HEURISTIC,
            candidate_count=1,
            selected_score=0.91,
            runtime_result=RepairOutcome.RECOVERED,
            llm_evidence=current_llm_evidence(eligible=False),
        )
    )
    mark_test_failed(node_id)

    written = finalize_test(node_id)

    loaded = load_repair_record(written[0])
    assert loaded.test_result is RepairTestOutcome.FAILED


def test_llm_eligibility_is_recordable_while_fallback_is_disabled() -> None:
    configure_runtime(enabled=True)

    evidence = current_llm_evidence(eligible=True)

    assert llm_fallback_enabled() is False
    assert evidence.enabled is False
    assert evidence.eligible is True
    assert evidence.call_attempted is False
    assert evidence.response_received is False
    assert evidence.provider is None
    assert evidence.model is None
    assert evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


def test_enabled_llm_runtime_exposes_model_timeout_and_pre_call_evidence() -> None:
    configure_runtime(
        enabled=True,
        llm_enabled=True,
        llm_model="  qwen2.5-coder:7b  ",
        llm_timeout_seconds=12.5,
    )

    configuration = current_llm_configuration()
    evidence = current_llm_evidence(eligible=True)

    assert llm_fallback_enabled() is True
    assert configuration.enabled is True
    assert configuration.model == "qwen2.5-coder:7b"
    assert configuration.timeout_seconds == 12.5
    assert evidence.enabled is True
    assert evidence.eligible is True
    assert evidence.call_attempted is False
    assert evidence.response_received is False
    assert evidence.provider == "ollama"
    assert evidence.model == "qwen2.5-coder:7b"
    assert evidence.outcome is LLMEvidenceOutcome.NOT_CALLED
    assert evidence.latency_ms is None


def test_completed_llm_evidence_records_one_provider_attempt() -> None:
    configure_runtime(
        enabled=True,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
    )

    evidence = completed_llm_evidence(
        outcome=LLMEvidenceOutcome.INVALID_SCHEMA,
        response_received=True,
        latency_ms=7,
    )

    assert evidence.enabled is True
    assert evidence.eligible is True
    assert evidence.call_attempted is True
    assert evidence.response_received is True
    assert evidence.provider == "ollama"
    assert evidence.model == "qwen2.5-coder:7b"
    assert evidence.outcome is LLMEvidenceOutcome.INVALID_SCHEMA
    assert evidence.latency_ms == 7


def test_completed_llm_evidence_requires_enabled_llm_configuration() -> None:
    configure_runtime(enabled=True)

    with pytest.raises(RuntimeError, match="enabled runtime configuration"):
        completed_llm_evidence(
            outcome=LLMEvidenceOutcome.TIMEOUT,
            response_received=False,
            latency_ms=1,
        )


def test_llm_runtime_cannot_be_enabled_without_tre() -> None:
    with pytest.raises(ValueError, match="requires TestRepairEngine"):
        configure_runtime(
            enabled=False,
            llm_enabled=True,
            llm_model="qwen2.5-coder:7b",
        )


def test_llm_runtime_requires_model_when_enabled() -> None:
    with pytest.raises(ValueError, match="non-blank Ollama model"):
        configure_runtime(enabled=True, llm_enabled=True, llm_model="   ")


def test_llm_runtime_rejects_nonpositive_or_nonfinite_timeout() -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        configure_runtime(enabled=True, llm_timeout_seconds=0)

    with pytest.raises(ValueError, match="finite and positive"):
        configure_runtime(enabled=True, llm_timeout_seconds=float("inf"))


def test_reset_runtime_clears_llm_configuration() -> None:
    configure_runtime(
        enabled=True,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
        llm_timeout_seconds=12.5,
    )

    reset_runtime()
    configuration = current_llm_configuration()

    assert configuration.enabled is False
    assert configuration.model is None
    assert llm_fallback_enabled() is False
