"""In-process runtime state for pytest-correlated repair evidence."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from test_repair_engine.contracts import RepairRecord, TestOutcome
from test_repair_engine.recording import write_repair_record

_CURRENT_TEST_NODE: ContextVar[str | None] = ContextVar(
    "test_repair_engine_current_test_node",
    default=None,
)


@dataclass(slots=True)
class RuntimeState:
    """Small process-local state owned by the pytest integration."""

    enabled: bool = False
    run_id: str | None = None
    output_dir: Path = Path("repair-records")
    pending_by_test: dict[str, list[RepairRecord]] = field(default_factory=dict)
    failed_tests: set[str] = field(default_factory=set)


_STATE = RuntimeState()


def configure_runtime(*, enabled: bool, output_dir: Path | str = "repair-records") -> None:
    """Reset and configure runtime state for one pytest session."""

    _STATE.enabled = enabled
    _STATE.run_id = f"run-{uuid4()}" if enabled else None
    _STATE.output_dir = Path(output_dir)
    _STATE.pending_by_test.clear()
    _STATE.failed_tests.clear()
    _CURRENT_TEST_NODE.set(None)


def reset_runtime() -> None:
    """Return runtime state to its disabled default."""

    configure_runtime(enabled=False)


def repair_enabled() -> bool:
    """Return whether runtime recovery is enabled for this process."""

    return _STATE.enabled


def current_run_id() -> str:
    """Return the active run ID for persisted repair records."""

    if not _STATE.enabled or _STATE.run_id is None:
        raise RuntimeError("TestRepairEngine runtime is not enabled.")
    return _STATE.run_id


def set_current_test_node(node_id: str) -> None:
    """Associate subsequent repair attempts with one pytest node ID."""

    _CURRENT_TEST_NODE.set(node_id)


def current_test_node_id() -> str | None:
    """Return the current pytest node ID when one is active."""

    return _CURRENT_TEST_NODE.get()


def clear_current_test_node() -> None:
    """Clear the active pytest node association."""

    _CURRENT_TEST_NODE.set(None)


def register_repair(record: RepairRecord) -> None:
    """Keep one runtime repair pending until the original test finishes."""

    if not _STATE.enabled:
        return

    node_id = record.test_node_id or current_test_node_id()
    if node_id is None:
        finalized = record.model_copy(update={"test_result": TestOutcome.UNKNOWN})
        _persist(finalized)
        return

    _STATE.pending_by_test.setdefault(node_id, []).append(record)


def mark_test_failed(node_id: str) -> None:
    """Remember any failed pytest phase for final test-outcome correlation."""

    if _STATE.enabled:
        _STATE.failed_tests.add(node_id)


def finalize_test(node_id: str) -> list[Path]:
    """Finalize and persist all repairs after the original pytest test ends."""

    records = _STATE.pending_by_test.pop(node_id, [])
    failed = node_id in _STATE.failed_tests
    _STATE.failed_tests.discard(node_id)

    outcome = TestOutcome.FAILED if failed else TestOutcome.PASSED
    written: list[Path] = []
    for record in records:
        finalized = record.model_copy(update={"test_result": outcome})
        written.append(_persist(finalized))
    return written


def _persist(record: RepairRecord) -> Path:
    destination = _STATE.output_dir / f"{record.repair_id}.json"
    return write_repair_record(record, destination)
