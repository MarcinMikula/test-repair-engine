"""Unit tests for pytest-correlated runtime repair evidence."""

from pathlib import Path

import pytest

from test_repair_engine.contracts import (
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.contracts import TestOutcome as RepairTestOutcome
from test_repair_engine.recording import load_repair_record
from test_repair_engine.runtime import (
    configure_runtime,
    current_run_id,
    finalize_test,
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
        )
    )
    mark_test_failed(node_id)

    written = finalize_test(node_id)

    loaded = load_repair_record(written[0])
    assert loaded.test_result is RepairTestOutcome.FAILED
