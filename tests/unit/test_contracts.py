"""Unit tests for TestRepairEngine public contracts."""

import pytest
from pydantic import ValidationError

from test_repair_engine.contracts import (
    CartographerTraceability,
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


def test_repair_request_can_exist_without_cartographer() -> None:
    request = RepairRequest(
        action=RepairAction.FILL,
        original_locator="[data-testid='search-input']",
    )

    assert request.project_reference is None
    assert request.cartographer_traceability is None


def test_repair_request_can_carry_opaque_cartographer_references() -> None:
    request = RepairRequest(
        action=RepairAction.CLICK,
        original_locator="[data-testid='search-submit']",
        project_reference=ProjectReference(
            profile_id="project-profile-main",
            revision=2,
            configuration_fingerprint="configuration-fingerprint-value",
        ),
        cartographer_traceability=CartographerTraceability(
            context_id="context-search",
            process_id="process-search",
            element_id="element-search-submit",
        ),
    )

    assert request.project_reference is not None
    assert request.project_reference.revision == 2
    assert request.cartographer_traceability is not None
    assert request.cartographer_traceability.element_id == "element-search-submit"


def test_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RepairRequest(
            action=RepairAction.CLICK,
            original_locator="[data-testid='search-submit']",
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
        )


def test_recovered_result_requires_repair_method() -> None:
    with pytest.raises(
        ValidationError,
        match="repair_method",
    ):
        RepairResult(
            outcome=RepairOutcome.RECOVERED,
            replacement_locator="[data-testid='catalog-search-input']",
        )


def test_failed_result_does_not_require_replacement() -> None:
    result = RepairResult(
        outcome=RepairOutcome.FAILED,
        reason="No suitable candidate found.",
    )

    assert result.replacement_locator is None
    assert result.repair_method is None


def test_repair_record_separates_runtime_and_final_test_result() -> None:
    record = RepairRecord(
        run_id="run-001",
        test_node_id="tests/e2e/test_search.py::test_product_search",
        action=RepairAction.FILL,
        original_locator="[data-testid='search-input']",
        replacement_locator="[data-testid='catalog-search-input']",
        repair_method=RepairMethod.HEURISTIC,
        runtime_result=RepairOutcome.RECOVERED,
    )

    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.test_result is RepairTestOutcome.UNKNOWN


def test_recovered_record_requires_consistent_repair_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match="replacement_locator",
    ):
        RepairRecord(
            run_id="run-001",
            action=RepairAction.FILL,
            original_locator="[data-testid='search-input']",
            repair_method=RepairMethod.HEURISTIC,
            runtime_result=RepairOutcome.RECOVERED,
        )
