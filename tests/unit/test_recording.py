"""Unit tests for RepairRecord persistence."""

from pathlib import Path

import pytest

from test_repair_engine.contracts import (
    ProjectReference,
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.contracts import TestOutcome as RepairTestOutcome
from test_repair_engine.recording import load_repair_record, write_repair_record

pytestmark = pytest.mark.unit


VALID_FINGERPRINT = "a" * 64


def test_repair_record_round_trip(tmp_path: Path) -> None:
    original = RepairRecord(
        run_id="run-001",
        test_node_id="tests/e2e/test_search.py::test_product_search",
        action=RepairAction.FILL,
        original_locator="search-input",
        replacement_locator="catalog-search-input",
        repair_method=RepairMethod.HEURISTIC,
        candidate_count=1,
        selected_score=0.91,
        runtime_result=RepairOutcome.RECOVERED,
        test_result=RepairTestOutcome.PASSED,
        project_reference=ProjectReference(
            project_profile_id="project-profile-main",
            project_profile_revision=2,
            configuration_fingerprint=VALID_FINGERPRINT,
        ),
    )

    destination = tmp_path / "repair-record.json"

    written_path = write_repair_record(original, destination)
    loaded = load_repair_record(written_path)

    assert loaded == original


def test_writer_creates_parent_directory(tmp_path: Path) -> None:
    record = RepairRecord(
        run_id="run-002",
        action=RepairAction.CLICK,
        original_locator="search-submit",
        runtime_result=RepairOutcome.FAILED,
    )

    destination = tmp_path / "nested" / "repair-record.json"

    write_repair_record(record, destination)

    assert destination.exists()


def test_persisted_record_contains_schema_version(tmp_path: Path) -> None:
    record = RepairRecord(
        run_id="run-003",
        action=RepairAction.CLICK,
        original_locator="search-submit",
        runtime_result=RepairOutcome.ESCALATED,
    )

    destination = write_repair_record(
        record,
        tmp_path / "repair-record.json",
    )

    persisted = destination.read_text(encoding="utf-8")

    assert '"schema_version": "0.1"' in persisted
