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


class LocatorKind(StrEnum):
    """Locator families currently understood by TestRepairEngine."""

    TEST_ID = "test_id"
    ROLE = "role"


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


class LLMEvidenceOutcome(StrEnum):
    """Observed result of the bounded LLM decision boundary."""

    NOT_CALLED = "not_called"
    CALL_FAILED = "call_failed"
    TIMEOUT = "timeout"
    INVALID_JSON = "invalid_json"
    INVALID_SCHEMA = "invalid_schema"
    ABSTAINED = "abstained"
    OUTSIDE_ALLOWLIST = "outside_allowlist"
    VALIDATED_SELECTION = "validated_selection"


class LLMEvidence(StrictContract):
    """Persistable facts describing whether and how the LLM boundary was used.

    ``enabled`` is runtime configuration. ``eligible`` is the deterministic
    decision that the current repair attempt qualifies for bounded LLM fallback.
    They are intentionally independent: an eligible ambiguity can occur while
    LLM fallback is disabled.
    """

    enabled: bool
    eligible: bool
    call_attempted: bool
    response_received: bool
    provider: Literal["ollama"] | None = None
    model: str | None = None
    outcome: LLMEvidenceOutcome
    latency_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def evidence_state_must_be_consistent(self) -> LLMEvidence:
        """Reject impossible combinations of LLM runtime evidence."""

        if self.enabled:
            if self.provider != "ollama":
                raise ValueError("Enabled LLM evidence requires provider='ollama'.")
            if self.model is None or not self.model.strip():
                raise ValueError("Enabled LLM evidence requires a non-blank model.")
        elif self.provider is not None or self.model is not None:
            raise ValueError("Disabled LLM evidence must not claim provider or model usage.")

        if self.call_attempted and (not self.enabled or not self.eligible):
            raise ValueError("An LLM call requires both enabled and eligible to be true.")

        if self.response_received and not self.call_attempted:
            raise ValueError("An LLM response cannot exist without a call attempt.")

        if not self.call_attempted:
            if self.outcome is not LLMEvidenceOutcome.NOT_CALLED:
                raise ValueError("No-call LLM evidence requires outcome='not_called'.")
            if self.latency_ms is not None:
                raise ValueError("No-call LLM evidence must not contain latency_ms.")
            return self

        if self.outcome is LLMEvidenceOutcome.NOT_CALLED:
            raise ValueError("An attempted LLM call cannot have outcome='not_called'.")
        if self.latency_ms is None:
            raise ValueError("An attempted LLM call requires latency_ms.")

        response_outcomes = {
            LLMEvidenceOutcome.INVALID_JSON,
            LLMEvidenceOutcome.INVALID_SCHEMA,
            LLMEvidenceOutcome.ABSTAINED,
            LLMEvidenceOutcome.OUTSIDE_ALLOWLIST,
            LLMEvidenceOutcome.VALIDATED_SELECTION,
        }
        no_response_outcomes = {
            LLMEvidenceOutcome.CALL_FAILED,
            LLMEvidenceOutcome.TIMEOUT,
        }

        if self.outcome in response_outcomes and not self.response_received:
            raise ValueError("This LLM outcome requires response_received=true.")
        if self.outcome in no_response_outcomes and self.response_received:
            raise ValueError("This LLM outcome requires response_received=false.")

        return self


class ProjectReference(StrictContract):
    """Opaque TestCartographer ProjectProfile identity used for one repair.

    Field names intentionally match the bounded ProjectProfile reference naming
    used by TestCartographer, while the two packages remain independent.
    """

    project_profile_id: str = Field(min_length=1)
    project_profile_revision: int = Field(ge=1)
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    locator_kind: LocatorKind = LocatorKind.TEST_ID
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
    candidate_count: int = Field(default=0, ge=0)
    selected_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str | None = None

    @model_validator(mode="after")
    def recovered_result_requires_validated_candidate(self) -> RepairResult:
        """A successful recovery must identify how and what was recovered."""

        if self.outcome is RepairOutcome.RECOVERED:
            if not self.replacement_locator:
                raise ValueError("A recovered repair result requires replacement_locator.")
            if self.repair_method is None:
                raise ValueError("A recovered repair result requires repair_method.")
            if self.candidate_count < 1:
                raise ValueError("A recovered repair result requires at least one candidate.")

        return self


class RepairRecord(StrictContract):
    """Persistable evidence describing one repair attempt.

    Runtime repair success and final test success are intentionally separate.
    The pytest integration finalizes ``test_result`` only after the unchanged
    original test finishes.
    """

    schema_version: Literal["0.1", "0.2"] = "0.2"

    repair_id: UUID = Field(default_factory=uuid4)
    run_id: str = Field(min_length=1)

    test_node_id: str | None = None
    page_object: str | None = None
    method_name: str | None = None

    action: RepairAction
    locator_kind: LocatorKind = LocatorKind.TEST_ID
    original_locator: str = Field(min_length=1)
    replacement_locator: str | None = None

    repair_method: RepairMethod | None = None
    candidate_count: int = Field(default=0, ge=0)
    selected_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str | None = None
    runtime_result: RepairOutcome
    test_result: TestOutcome = TestOutcome.UNKNOWN
    llm_evidence: LLMEvidence | None = None

    project_reference: ProjectReference | None = None
    cartographer_traceability: CartographerTraceability | None = None

    @model_validator(mode="after")
    def schema_version_must_match_llm_evidence(self) -> RepairRecord:
        """Keep historical v0.1 records distinct from new v0.2 evidence."""

        if self.schema_version == "0.1":
            if self.llm_evidence is not None:
                raise ValueError("RepairRecord v0.1 must not contain llm_evidence.")
        elif self.llm_evidence is None:
            raise ValueError("RepairRecord v0.2 requires llm_evidence.")

        return self

    @model_validator(mode="after")
    def recovered_record_requires_validated_candidate(self) -> RepairRecord:
        """Persist only internally consistent successful repair evidence."""

        if self.runtime_result is RepairOutcome.RECOVERED:
            if not self.replacement_locator:
                raise ValueError("A recovered repair record requires replacement_locator.")
            if self.repair_method is None:
                raise ValueError("A recovered repair record requires repair_method.")
            if self.candidate_count < 1:
                raise ValueError("A recovered repair record requires at least one candidate.")

        return self
