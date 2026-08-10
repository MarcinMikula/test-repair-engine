"""pytest integration for opt-in runtime repair and final test correlation."""

from __future__ import annotations

from pathlib import Path

import pytest

from test_repair_engine.runtime import (
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


def pytest_configure(config: pytest.Config) -> None:
    enabled = bool(config.getoption("--test-repair-engine"))
    output_dir = Path(str(config.getoption("--test-repair-record-dir")))
    configure_runtime(enabled=enabled, output_dir=output_dir)


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
