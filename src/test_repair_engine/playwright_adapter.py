"""Playwright-specific bounded collection and retry for locator drift."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter_ns

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from test_repair_engine.candidate_finder import (
    CandidateSelectionStatus,
    LocatorCandidate,
    select_candidate,
)
from test_repair_engine.contracts import (
    CartographerTraceability,
    LLMEvidence,
    LLMEvidenceOutcome,
    LocatorKind,
    ProjectReference,
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.ollama_provider import (
    OllamaDecisionOutcome,
    OllamaDecisionResult,
    OllamaProvider,
)
from test_repair_engine.runtime import (
    completed_llm_evidence,
    current_llm_configuration,
    current_llm_evidence,
    current_run_id,
    current_test_node_id,
    register_repair,
    repair_enabled,
)

_DEFAULT_TEST_ID_ATTRIBUTE = "data-testid"
_MAX_TEST_ID_CANDIDATES = 50
_NO_RESPONSE_OUTCOMES = {
    OllamaDecisionOutcome.CALL_FAILED,
    OllamaDecisionOutcome.TIMEOUT,
}
_PROVIDER_TO_EVIDENCE_OUTCOME = {
    OllamaDecisionOutcome.CALL_FAILED: LLMEvidenceOutcome.CALL_FAILED,
    OllamaDecisionOutcome.TIMEOUT: LLMEvidenceOutcome.TIMEOUT,
    OllamaDecisionOutcome.INVALID_JSON: LLMEvidenceOutcome.INVALID_JSON,
    OllamaDecisionOutcome.INVALID_SCHEMA: LLMEvidenceOutcome.INVALID_SCHEMA,
    OllamaDecisionOutcome.ABSTAINED: LLMEvidenceOutcome.ABSTAINED,
    OllamaDecisionOutcome.OUTSIDE_ALLOWLIST: LLMEvidenceOutcome.OUTSIDE_ALLOWLIST,
    OllamaDecisionOutcome.VALIDATED_SELECTION: LLMEvidenceOutcome.VALIDATED_SELECTION,
}


def collect_test_id_candidates(
    page: Page,
    *,
    test_id_attribute: str = _DEFAULT_TEST_ID_ATTRIBUTE,
    max_candidates: int = _MAX_TEST_ID_CANDIDATES,
) -> list[LocatorCandidate]:
    """Collect bounded structural metadata for the configured test-id attribute."""

    locator = page.locator(f"[{test_id_attribute}]")
    count = min(locator.count(), max_candidates)
    candidates: list[LocatorCandidate] = []

    for index in range(count):
        element = locator.nth(index)
        try:
            test_id = element.get_attribute(test_id_attribute)
            if not test_id:
                continue

            tag_name = element.evaluate("element => element.tagName.toLowerCase()")
            role = element.get_attribute("role")
            visible = element.is_visible()
            enabled = element.is_enabled()
            try:
                editable = element.is_editable()
            except PlaywrightError:
                # Playwright may reject editability probes for element types where
                # editability is not applicable, such as ordinary buttons. Keep the
                # otherwise valid candidate and represent it as non-editable.
                editable = False

            candidates.append(
                LocatorCandidate(
                    test_id=test_id,
                    tag_name=str(tag_name),
                    role=role,
                    visible=visible,
                    enabled=enabled,
                    editable=editable,
                )
            )
        except PlaywrightError:
            continue

    return candidates


def recover_test_id_action(
    page: Page,
    *,
    action: RepairAction,
    original_test_id: str,
    retry: Callable[[str], None],
    test_id_attribute: str = _DEFAULT_TEST_ID_ATTRIBUTE,
    page_object: str | None = None,
    method_name: str | None = None,
    project_reference: ProjectReference | None = None,
    cartographer_traceability: CartographerTraceability | None = None,
) -> bool:
    """Attempt one bounded repair and at most one retry of the failed interaction.

    Deterministic selection always has precedence. Ollama is eligible only for an
    explicitly bounded ambiguity and only when the LLM fallback is enabled. The
    callback may close over a runtime interaction value, but TestRepairEngine
    never sends, stores, or inspects that value.
    """

    if not repair_enabled():
        return False

    test_node_id = current_test_node_id()
    candidates = collect_test_id_candidates(
        page,
        test_id_attribute=test_id_attribute,
    )
    selection = select_candidate(original_test_id, action, candidates)
    original_match_count = sum(candidate.test_id == original_test_id for candidate in candidates)

    if original_match_count == 1:
        register_repair(
            RepairRecord(
                run_id=current_run_id(),
                test_node_id=test_node_id,
                page_object=page_object,
                method_name=method_name,
                action=action,
                locator_kind=LocatorKind.TEST_ID,
                original_locator=original_test_id,
                candidate_count=selection.candidate_count,
                selected_score=None,
                reason=(
                    "Original test-id still resolves exactly once; "
                    "locator substitution is not authorized."
                ),
                runtime_result=RepairOutcome.FAILED,
                llm_evidence=current_llm_evidence(eligible=False),
                project_reference=project_reference,
                cartographer_traceability=cartographer_traceability,
            )
        )
        return False

    llm_eligible = selection.status is CandidateSelectionStatus.AMBIGUOUS
    llm_evidence = current_llm_evidence(eligible=llm_eligible)

    replacement_test_id: str | None = None
    repair_method: RepairMethod | None = None
    selected_score = selection.score
    reason = selection.reason

    if selection.candidate is not None:
        replacement_test_id = selection.candidate.test_id
        repair_method = RepairMethod.HEURISTIC
    elif llm_eligible and llm_evidence.enabled:
        # Once the provider is called, no deterministic score may be recorded as
        # though it described the LLM decision or a selected candidate.
        selected_score = None
        replacement_test_id, llm_evidence, reason = _resolve_llm_ambiguity(
            action=action,
            original_test_id=original_test_id,
            shortlist=selection.shortlist,
            page_object=page_object,
            method_name=method_name,
        )
        if replacement_test_id is not None:
            repair_method = RepairMethod.LLM

    if replacement_test_id is None:
        register_repair(
            RepairRecord(
                run_id=current_run_id(),
                test_node_id=test_node_id,
                page_object=page_object,
                method_name=method_name,
                action=action,
                locator_kind=LocatorKind.TEST_ID,
                original_locator=original_test_id,
                candidate_count=selection.candidate_count,
                selected_score=selected_score,
                reason=reason,
                runtime_result=RepairOutcome.FAILED,
                llm_evidence=llm_evidence,
                project_reference=project_reference,
                cartographer_traceability=cartographer_traceability,
            )
        )
        return False

    try:
        retry(replacement_test_id)
    except PlaywrightError:
        register_repair(
            RepairRecord(
                run_id=current_run_id(),
                test_node_id=test_node_id,
                page_object=page_object,
                method_name=method_name,
                action=action,
                locator_kind=LocatorKind.TEST_ID,
                original_locator=original_test_id,
                replacement_locator=replacement_test_id,
                repair_method=repair_method,
                candidate_count=selection.candidate_count,
                selected_score=selected_score,
                reason="Selected candidate did not recover the Playwright interaction.",
                runtime_result=RepairOutcome.FAILED,
                llm_evidence=llm_evidence,
                project_reference=project_reference,
                cartographer_traceability=cartographer_traceability,
            )
        )
        return False

    register_repair(
        RepairRecord(
            run_id=current_run_id(),
            test_node_id=test_node_id,
            page_object=page_object,
            method_name=method_name,
            action=action,
            locator_kind=LocatorKind.TEST_ID,
            original_locator=original_test_id,
            replacement_locator=replacement_test_id,
            repair_method=repair_method,
            candidate_count=selection.candidate_count,
            selected_score=selected_score,
            reason=reason,
            runtime_result=RepairOutcome.RECOVERED,
            llm_evidence=llm_evidence,
            project_reference=project_reference,
            cartographer_traceability=cartographer_traceability,
        )
    )
    return True


def _resolve_llm_ambiguity(
    *,
    action: RepairAction,
    original_test_id: str,
    shortlist: tuple[LocatorCandidate, ...],
    page_object: str | None,
    method_name: str | None,
) -> tuple[str | None, LLMEvidence, str]:
    configuration = current_llm_configuration()
    if not configuration.enabled or configuration.model is None:
        raise RuntimeError("LLM ambiguity resolution requires enabled runtime configuration.")

    provider = OllamaProvider(
        model=configuration.model,
        timeout_seconds=configuration.timeout_seconds,
    )
    started_ns = perf_counter_ns()
    decision = provider.decide(
        action=action,
        original_test_id=original_test_id,
        shortlist=shortlist,
        page_object=page_object,
        method_name=method_name,
    )
    latency_ms = max(0, (perf_counter_ns() - started_ns) // 1_000_000)

    evidence_outcome = _PROVIDER_TO_EVIDENCE_OUTCOME[decision.outcome]
    response_received = decision.outcome not in _NO_RESPONSE_OUTCOMES
    replacement_test_id = _validated_execution_selection(decision, shortlist)

    if (
        decision.outcome is OllamaDecisionOutcome.VALIDATED_SELECTION
        and replacement_test_id is None
    ):
        # Defense in depth: execution re-validates the exact shortlist even if a
        # buggy provider implementation claims a validated selection.
        evidence_outcome = LLMEvidenceOutcome.OUTSIDE_ALLOWLIST
        response_received = True

    evidence = completed_llm_evidence(
        outcome=evidence_outcome,
        response_received=response_received,
        latency_ms=latency_ms,
    )

    if replacement_test_id is not None:
        return (
            replacement_test_id,
            evidence,
            "Validated Ollama shortlist selection authorized one retry.",
        )

    if decision.outcome is OllamaDecisionOutcome.ABSTAINED:
        return None, evidence, "Ollama abstained from the bounded ambiguity."

    if decision.outcome is OllamaDecisionOutcome.VALIDATED_SELECTION:
        return (
            None,
            evidence,
            "Ollama selection failed exact execution allowlist validation.",
        )

    return (
        None,
        evidence,
        decision.reason or "Ollama fallback did not authorize a retry.",
    )


def _validated_execution_selection(
    decision: OllamaDecisionResult,
    shortlist: tuple[LocatorCandidate, ...],
) -> str | None:
    if decision.outcome is not OllamaDecisionOutcome.VALIDATED_SELECTION:
        return None
    if decision.selected_test_id is None:
        return None

    allowed_ids = {candidate.test_id for candidate in shortlist}
    if decision.selected_test_id not in allowed_ids:
        return None
    return decision.selected_test_id
