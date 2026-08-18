"""pytest integration for opt-in runtime repair and final test correlation."""

from __future__ import annotations

from pathlib import Path

import pytest

from test_repair_engine.runtime import (
    DEFAULT_LLM_TIMEOUT_SECONDS,
    clear_current_test_node,
    configure_runtime,
    finalize_test,
    mark_test_failed,
    repair_enabled,
    reset_runtime,
    set_current_test_node,
)


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("test-repair-engine")
    group.addoption(
        "--test-repair-engine",
        action="store_true",
        default=False,
        help="Enable bounded TestRepairEngine runtime recovery.",
    )
    group.addoption(
        "--test-repair-record-dir",
        action="store",
        default="repair-records",
        metavar="PATH",
        help="Directory for finalized RepairRecord JSON files.",
    )
    group.addoption(
        "--test-repair-engine-llm",
        action="store_true",
        default=False,
        help="Enable local Ollama fallback only for bounded deterministic ambiguity.",
    )
    group.addoption(
        "--test-repair-engine-llm-model",
        action="store",
        default=None,
        metavar="MODEL",
        help="Ollama model used by the bounded LLM fallback when enabled.",
    )
    group.addoption(
        "--test-repair-engine-llm-timeout",
        action="store",
        type=float,
        default=DEFAULT_LLM_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help="Finite timeout for one local Ollama decision call.",
    )


def pytest_configure(config: pytest.Config) -> None:
    enabled = bool(config.getoption("--test-repair-engine"))
    output_dir = Path(str(config.getoption("--test-repair-record-dir")))
    llm_enabled = bool(config.getoption("--test-repair-engine-llm"))
    llm_model_option = config.getoption("--test-repair-engine-llm-model")
    llm_model = str(llm_model_option) if llm_model_option is not None else None
    llm_timeout_seconds = float(config.getoption("--test-repair-engine-llm-timeout"))

    try:
        configure_runtime(
            enabled=enabled,
            output_dir=output_dir,
            llm_enabled=llm_enabled,
            llm_model=llm_model,
            llm_timeout_seconds=llm_timeout_seconds,
        )
    except ValueError as exc:
        raise pytest.UsageError(str(exc)) from exc


def pytest_runtest_setup(item: pytest.Item) -> None:
    if repair_enabled():
        set_current_test_node(item.nodeid)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if not repair_enabled():
        return

    if report.failed or report.skipped:
        mark_test_failed(report.nodeid)

    if report.when == "teardown":
        finalize_test(report.nodeid)
        clear_current_test_node()


def pytest_unconfigure(config: pytest.Config) -> None:
    reset_runtime()
