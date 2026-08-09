"""Persistence helpers for TestRepairEngine repair evidence."""

from __future__ import annotations

from pathlib import Path

from test_repair_engine.contracts import RepairRecord


def write_repair_record(record: RepairRecord, destination: Path) -> Path:
    """Persist one RepairRecord as UTF-8 JSON using atomic replacement."""

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        record.model_dump_json(indent=2),
        encoding="utf-8",
    )
    temporary.replace(destination)

    return destination


def load_repair_record(source: Path) -> RepairRecord:
    """Load and validate one persisted RepairRecord."""

    source = Path(source)
    return RepairRecord.model_validate_json(source.read_text(encoding="utf-8"))
