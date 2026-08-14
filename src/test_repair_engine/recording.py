"""Persistence helpers for TestRepairEngine repair evidence."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from test_repair_engine.contracts import RepairRecord


def write_repair_record(record: RepairRecord, destination: Path) -> Path:
    """Persist one RepairRecord as UTF-8 JSON without overwriting evidence."""

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(record.model_dump_json(indent=2))
            temporary_path = Path(temporary.name)

        # Publish the completed file atomically without replacing an existing
        # RepairRecord. os.link() fails with FileExistsError on collision.
        os.link(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return destination


def load_repair_record(source: Path) -> RepairRecord:
    """Load and validate one persisted RepairRecord."""

    source = Path(source)
    return RepairRecord.model_validate_json(source.read_text(encoding="utf-8"))
