"""Unit tests for pytest runtime correlation hooks."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from test_repair_engine.contracts import (
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.contracts import TestOutcome as RepairTestOutcome
from test_repair_engine.pytest_plugin import (
    pytest_configure,
    pytest_runtest_logreport,
    pytest_runtest_setup,
    pytest_unconfigure,
)
from test_repair_engine.recording import load_repair_record
from test_repair_engine.runtime import (
    current_llm_configuration,
    current_llm_evidence,
    current_run_id,
    llm_fallback_enabled,
    register_repair,
    reset_runtime,
)

pytestmark = pytest.mark.unit


class FakeConfig:
    def __init__(
        self,
        *,
        enabled: bool,
        output_dir: Path,
        llm_enabled: bool = False,
        llm_model: str | None = None,
        llm_timeout_seconds: float = 30.0,
    ) -> None:
        self.enabled = enabled
        self.output_dir = output_dir
        self.llm_enabled = llm_enabled
        self.llm_model = llm_model
        self.llm_timeout_seconds = llm_timeout_seconds

    def getoption(self, name: str) -> object:
        if name == "--test-repair-engine":
            return self.enabled
        if name == "--test-repair-record-dir":
            return str(self.output_dir)
        if name == "--test-repair-engine-llm":
            return self.llm_enabled
        if name == "--test-repair-engine-llm-model":
            return self.llm_model
        if name == "--test-repair-engine-llm-timeout":
            return self.llm_timeout_seconds
        raise AssertionError(f"Unexpected pytest option: {name}")


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    reset_runtime()
    yield
    reset_runtime()


def _register_recovered_record(node_id: str) -> None:
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


def test_pytest_hooks_finalize_repair_as_passed_after_clean_teardown(tmp_path: Path) -> None:
    node_id = "tests/e2e/test_search.py::test_product_search"
    config = FakeConfig(enabled=True, output_dir=tmp_path)
    pytest_configure(config)  # type: ignore[arg-type]
    pytest_runtest_setup(SimpleNamespace(nodeid=node_id))  # type: ignore[arg-type]
    _register_recovered_record(node_id)

    pytest_runtest_logreport(
        SimpleNamespace(nodeid=node_id, failed=False, skipped=False, when="call")
    )  # type: ignore[arg-type]
    pytest_runtest_logreport(
        SimpleNamespace(nodeid=node_id, failed=False, skipped=False, when="teardown")
    )  # type: ignore[arg-type]

    records = list(tmp_path.glob("*.json"))
    assert len(records) == 1
    assert load_repair_record(records[0]).test_result is RepairTestOutcome.PASSED

    pytest_unconfigure(config)  # type: ignore[arg-type]


def test_pytest_hooks_do_not_validate_repair_when_test_is_skipped(tmp_path: Path) -> None:
    node_id = "tests/e2e/test_search.py::test_product_search"
    config = FakeConfig(enabled=True, output_dir=tmp_path)
    pytest_configure(config)  # type: ignore[arg-type]
    pytest_runtest_setup(SimpleNamespace(nodeid=node_id))  # type: ignore[arg-type]
    _register_recovered_record(node_id)

    pytest_runtest_logreport(
        SimpleNamespace(nodeid=node_id, failed=False, skipped=True, when="call")
    )  # type: ignore[arg-type]
    pytest_runtest_logreport(
        SimpleNamespace(nodeid=node_id, failed=False, skipped=False, when="teardown")
    )  # type: ignore[arg-type]

    records = list(tmp_path.glob("*.json"))
    assert len(records) == 1
    assert load_repair_record(records[0]).test_result is RepairTestOutcome.FAILED

    pytest_unconfigure(config)  # type: ignore[arg-type]


def test_pytest_configure_exposes_explicit_llm_runtime_configuration(tmp_path: Path) -> None:
    config = FakeConfig(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
        llm_timeout_seconds=12.5,
    )

    pytest_configure(config)  # type: ignore[arg-type]

    configuration = current_llm_configuration()
    assert llm_fallback_enabled() is True
    assert configuration.model == "qwen2.5-coder:7b"
    assert configuration.timeout_seconds == 12.5

    pytest_unconfigure(config)  # type: ignore[arg-type]


def test_pytest_configure_rejects_llm_without_tre(tmp_path: Path) -> None:
    config = FakeConfig(
        enabled=False,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
    )

    with pytest.raises(pytest.UsageError, match="requires TestRepairEngine"):
        pytest_configure(config)  # type: ignore[arg-type]


def test_pytest_configure_rejects_enabled_llm_without_model(tmp_path: Path) -> None:
    config = FakeConfig(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model=None,
    )

    with pytest.raises(pytest.UsageError, match="non-blank Ollama model"):
        pytest_configure(config)  # type: ignore[arg-type]
