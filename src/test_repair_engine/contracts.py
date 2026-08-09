"""Core contracts shared across the TestRepairEngine runtime boundary.

The contracts deliberately describe repair facts without owning application
knowledge or TestCartographer state.

TestRepairEngine may carry TestCartographer identifiers as opaque traceability,
but it must not interpret their lifecycle or compatibility.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictContract(BaseModel):
    """Base model for versioned TestRepairEngine contracts."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class RepairAction(StrEnum):
    """Playwright interaction kinds supported by the first product slice."""

    CLICK = "click"
    FILL = "fill"


class RepairMethod(StrEnum):
    """Mechanism that produced a repair candidate."""

    HEURISTIC = "heuristic"
    LLM = "llm"


class RepairOutcome(StrEnum):
    """Result of the runtime recovery attempt itself."""

    NOT_ATTEMPTED = "not_attempted"
    RECOVERED = "recovered"
    FAILED = "failed"
    ESCALATED = "escalated"


class TestOutcome(StrEnum):
    """Final outcome of the original test after any runtime repair."""

    UNKNOWN = "unknown"
    PASSED = "passed"
    FAILED = "failed"


class ProjectReference(StrictContract):
    """Opaque reference to the TestCartographer project configuration.

    TestRepairEngine records this identity when it is supplied by the
    surrounding ecosystem.

    It does not interpret ProjectProfile compatibility, invalidation,
    environment changes, or workspace drift.
    """

    profile_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    configuration_fingerprint: str = Field(min_length=1)


class CartographerTraceability(StrictContract):
    """Optional references to TestCartographer knowledge artifacts.

    All fields are optional because TestRepairEngine must also work outside
    the wider ecosystem.
    """

    context_id: str | None = None
    process_id: str | None = None
    element_id: str | None = None


class RepairRequest(StrictContract):
    """Structural description of the failed interaction to repair.

    Runtime values used by an action, such as text entered into an input,
    deliberately do not belong to this persistable contract.
    """

    action: RepairAction
    original_locator: str = Field(min_length=1)

    test_node_id: str | None = None
    page_object: str | None = None
    method_name: str | None = None

    project_reference: ProjectReference | None = None
    cartographer_traceability: CartographerTraceability | None = None


class RepairResult(StrictContract):
    """Result returned by one completed TestRepairEngine recovery attempt."""

    outcome: RepairOutcome
    replacement_locator: str | None = None
    repair_method: RepairMethod | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def recovered_result_requires_validated_candidate(self) -> RepairResult:
        """A successful recovery must identify how and what was recovered."""

        if self.outcome is RepairOutcome.RECOVERED:
            if not self.replacement_locator:
                raise ValueError("A recovered repair result requires replacement_locator.")
            if self.repair_method is None:
                raise ValueError("A recovered repair result requires repair_method.")

        return self


class RepairRecord(StrictContract):
    """Persistable evidence describing one repair attempt.

    Runtime repair success and final test success are intentionally separate.

    Recovering one Playwright interaction does not prove that the original
    test passed. A later pytest integration will update ``test_result`` after
    the complete test finishes.
    """

    schema_version: Literal["0.1"] = "0.1"

    repair_id: UUID = Field(default_factory=uuid4)
    run_id: str = Field(min_length=1)

    test_node_id: str | None = None

    action: RepairAction
    original_locator: str = Field(min_length=1)
    replacement_locator: str | None = None

    repair_method: RepairMethod | None = None
    runtime_result: RepairOutcome
    test_result: TestOutcome = TestOutcome.UNKNOWN

    project_reference: ProjectReference | None = None
    cartographer_traceability: CartographerTraceability | None = None

    @model_validator(mode="after")
    def recovered_record_requires_validated_candidate(self) -> RepairRecord:
        """Persist only internally consistent successful repair evidence."""

        if self.runtime_result is RepairOutcome.RECOVERED:
            if not self.replacement_locator:
                raise ValueError("A recovered repair record requires replacement_locator.")
            if self.repair_method is None:
                raise ValueError("A recovered repair record requires repair_method.")

        return self
