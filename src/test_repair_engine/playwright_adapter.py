"""Playwright-specific bounded collection and retry for locator drift."""

from __future__ import annotations

from collections.abc import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from test_repair_engine.candidate_finder import LocatorCandidate, select_candidate
from test_repair_engine.contracts import (
    CartographerTraceability,
    LocatorKind,
    ProjectReference,
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.runtime import (
    current_run_id,
    current_test_node_id,
    register_repair,
    repair_enabled,
)

_MAX_TEST_ID_CANDIDATES = 50


def collect_test_id_candidates(
    page: Page,
    *,
    max_candidates: int = _MAX_TEST_ID_CANDIDATES,
) -> list[LocatorCandidate]:
    """Collect bounded structural metadata without values, text, HTML, or screenshots."""

    locator = page.locator("[data-testid]")
    count = min(locator.count(), max_candidates)
    candidates: list[LocatorCandidate] = []

    for index in range(count):
        element = locator.nth(index)
        try:
            test_id = element.get_attribute("data-testid")
            if not test_id:
                continue

            tag_name = element.evaluate("element => element.tagName.toLowerCase()")
            role = element.get_attribute("role")
            candidates.append(
                LocatorCandidate(
                    test_id=test_id,
                    tag_name=str(tag_name),
                    role=role,
                    visible=element.is_visible(),
                    enabled=element.is_enabled(),
                    editable=element.is_editable(),
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
    page_object: str | None = None,
    method_name: str | None = None,
    project_reference: ProjectReference | None = None,
    cartographer_traceability: CartographerTraceability | None = None,
) -> bool:
    """Attempt one bounded deterministic repair and retry the failed interaction.

    The callback may close over the runtime interaction value, but TestRepairEngine
    never stores or inspects that value.
    """

    if not repair_enabled():
        return False

    test_node_id = current_test_node_id()
    candidates = collect_test_id_candidates(page)
    selection = select_candidate(original_test_id, action, candidates)

    if selection.candidate is None:
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
                selected_score=selection.score,
                reason=selection.reason,
                runtime_result=RepairOutcome.FAILED,
                project_reference=project_reference,
                cartographer_traceability=cartographer_traceability,
            )
        )
        return False

    replacement_test_id = selection.candidate.test_id
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
                repair_method=RepairMethod.HEURISTIC,
                candidate_count=selection.candidate_count,
                selected_score=selection.score,
                reason="Selected candidate did not recover the Playwright interaction.",
                runtime_result=RepairOutcome.FAILED,
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
            repair_method=RepairMethod.HEURISTIC,
            candidate_count=selection.candidate_count,
            selected_score=selection.score,
            reason=selection.reason,
            runtime_result=RepairOutcome.RECOVERED,
            project_reference=project_reference,
            cartographer_traceability=cartographer_traceability,
        )
    )
    return True
