"""Unit tests for RepairRecord persistence."""

import json
from pathlib import Path

import pytest

from test_repair_engine.contracts import (
    LLMEvidence,
    LLMEvidenceOutcome,
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


def _disabled_llm_evidence() -> LLMEvidence:
    return LLMEvidence(
        enabled=False,
        eligible=False,
        call_attempted=False,
        response_received=False,
        outcome=LLMEvidenceOutcome.NOT_CALLED,
    )


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
        llm_evidence=_disabled_llm_evidence(),
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
        llm_evidence=_disabled_llm_evidence(),
    )

    destination = tmp_path / "nested" / "repair-record.json"

    write_repair_record(record, destination)

    assert destination.exists()


def test_writer_rejects_existing_record_without_mutating_it(tmp_path: Path) -> None:
    original = RepairRecord(
        run_id="run-original",
        action=RepairAction.CLICK,
        original_locator="search-submit",
        runtime_result=RepairOutcome.FAILED,
        llm_evidence=_disabled_llm_evidence(),
    )
    replacement = RepairRecord(
        run_id="run-replacement",
        action=RepairAction.CLICK,
        original_locator="different-submit",
        runtime_result=RepairOutcome.ESCALATED,
        llm_evidence=_disabled_llm_evidence(),
    )
    destination = tmp_path / "repair-record.json"

    write_repair_record(original, destination)
    original_bytes = destination.read_bytes()

    with pytest.raises(FileExistsError):
        write_repair_record(replacement, destination)

    assert destination.read_bytes() == original_bytes
    assert load_repair_record(destination) == original
    assert list(tmp_path.glob(".repair-record.json.*.tmp")) == []


def test_persisted_record_contains_v02_schema_and_llm_evidence(tmp_path: Path) -> None:
    record = RepairRecord(
        run_id="run-003",
        action=RepairAction.CLICK,
        original_locator="search-submit",
        runtime_result=RepairOutcome.ESCALATED,
        llm_evidence=_disabled_llm_evidence(),
    )

    destination = write_repair_record(
        record,
        tmp_path / "repair-record.json",
    )

    persisted = destination.read_text(encoding="utf-8")

    assert '"schema_version": "0.2"' in persisted
    assert '"llm_evidence"' in persisted
    assert '"outcome": "not_called"' in persisted


def test_writer_rejects_new_historical_v01_record(tmp_path: Path) -> None:
    record = RepairRecord(
        schema_version="0.1",
        run_id="run-historical-new",
        action=RepairAction.CLICK,
        original_locator="search-submit",
        runtime_result=RepairOutcome.FAILED,
    )
    destination = tmp_path / "must-not-write-v01.json"

    with pytest.raises(ValueError, match="current RepairRecord schema v0.2"):
        write_repair_record(record, destination)

    assert not destination.exists()


def test_loader_preserves_historical_v01_record_without_backfilling_llm_evidence(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "historical-v01.json"
    destination.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "run_id": "run-historical",
                "action": "click",
                "original_locator": "search-submit",
                "runtime_result": "failed",
            }
        ),
        encoding="utf-8",
    )

    loaded = load_repair_record(destination)

    assert loaded.schema_version == "0.1"
    assert loaded.run_id == "run-historical"
    assert loaded.llm_evidence is None
