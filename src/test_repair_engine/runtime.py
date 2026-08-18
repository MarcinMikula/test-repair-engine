"""In-process runtime state for pytest-correlated repair evidence."""

from __future__ import annotations

import math
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from test_repair_engine.contracts import (
    LLMEvidence,
    LLMEvidenceOutcome,
    RepairRecord,
    TestOutcome,
)
from test_repair_engine.recording import write_repair_record

DEFAULT_LLM_TIMEOUT_SECONDS = 30.0

_CURRENT_TEST_NODE: ContextVar[str | None] = ContextVar(
    "test_repair_engine_current_test_node",
    default=None,
)


@dataclass(frozen=True, slots=True)
class LLMRuntimeConfiguration:
    """Read-only snapshot of bounded LLM runtime configuration."""

    enabled: bool
    model: str | None
    timeout_seconds: float


@dataclass(slots=True)
class RuntimeState:
    """Small process-local state owned by the pytest integration."""

    enabled: bool = False
    run_id: str | None = None
    output_dir: Path = Path("repair-records")
    llm_enabled: bool = False
    llm_model: str | None = None
    llm_timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS
    pending_by_test: dict[str, list[RepairRecord]] = field(default_factory=dict)
    failed_tests: set[str] = field(default_factory=set)


_STATE = RuntimeState()


def configure_runtime(
    *,
    enabled: bool,
    output_dir: Path | str = "repair-records",
    llm_enabled: bool = False,
    llm_model: str | None = None,
    llm_timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS,
) -> None:
    """Reset and configure runtime state for one pytest session."""

    if llm_enabled and not enabled:
        raise ValueError("LLM fallback requires TestRepairEngine runtime recovery to be enabled.")
    if not math.isfinite(llm_timeout_seconds) or llm_timeout_seconds <= 0:
        raise ValueError("LLM timeout must be finite and positive.")

    normalized_model = llm_model.strip() if llm_model is not None else None
    if llm_enabled and not normalized_model:
        raise ValueError("LLM fallback requires a non-blank Ollama model.")

    _STATE.enabled = enabled
    _STATE.run_id = f"run-{uuid4()}" if enabled else None
    _STATE.output_dir = Path(output_dir)
    _STATE.llm_enabled = llm_enabled
    _STATE.llm_model = normalized_model if llm_enabled else None
    _STATE.llm_timeout_seconds = float(llm_timeout_seconds)
    _STATE.pending_by_test.clear()
    _STATE.failed_tests.clear()
    _CURRENT_TEST_NODE.set(None)


def reset_runtime() -> None:
    """Return runtime state to its disabled default."""

    configure_runtime(enabled=False)


def repair_enabled() -> bool:
    """Return whether runtime recovery is enabled for this process."""

    return _STATE.enabled


def llm_fallback_enabled() -> bool:
    """Return whether bounded LLM fallback is explicitly enabled."""

    return _STATE.enabled and _STATE.llm_enabled


def current_llm_configuration() -> LLMRuntimeConfiguration:
    """Return the current bounded LLM runtime configuration."""

    return LLMRuntimeConfiguration(
        enabled=llm_fallback_enabled(),
        model=_STATE.llm_model if llm_fallback_enabled() else None,
        timeout_seconds=_STATE.llm_timeout_seconds,
    )


def current_llm_evidence(*, eligible: bool) -> LLMEvidence:
    """Build truthful no-call evidence for one deterministic repair decision."""

    configuration = current_llm_configuration()
    if configuration.enabled:
        return LLMEvidence(
            enabled=True,
            eligible=eligible,
            call_attempted=False,
            response_received=False,
            provider="ollama",
            model=configuration.model,
            outcome=LLMEvidenceOutcome.NOT_CALLED,
        )

    return LLMEvidence(
        enabled=False,
        eligible=eligible,
        call_attempted=False,
        response_received=False,
        outcome=LLMEvidenceOutcome.NOT_CALLED,
    )


def completed_llm_evidence(
    *,
    outcome: LLMEvidenceOutcome,
    response_received: bool,
    latency_ms: int,
) -> LLMEvidence:
    """Build truthful evidence for one completed bounded provider attempt."""

    configuration = current_llm_configuration()
    if not configuration.enabled or configuration.model is None:
        raise RuntimeError("Completed LLM evidence requires enabled runtime configuration.")

    return LLMEvidence(
        enabled=True,
        eligible=True,
        call_attempted=True,
        response_received=response_received,
        provider="ollama",
        model=configuration.model,
        outcome=outcome,
        latency_ms=latency_ms,
    )


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
