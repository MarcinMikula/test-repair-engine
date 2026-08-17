"""Unit tests for deterministic locator candidate selection."""

import pytest

from test_repair_engine.candidate_finder import (
    CandidateSelectionStatus,
    LocatorCandidate,
    score_test_id,
    select_candidate,
)
from test_repair_engine.contracts import RepairAction

pytestmark = pytest.mark.unit


def test_score_prefers_token_preserving_test_id_drift() -> None:
    preserved = score_test_id("search-input", "catalog-search-input")
    weaker = score_test_id("search-input", "search-submit")

    assert preserved > weaker
    assert preserved >= 0.60


def test_fill_selects_unique_editable_candidate() -> None:
    candidates = [
        LocatorCandidate(
            test_id="catalog-search-input",
            tag_name="input",
            editable=True,
        ),
        LocatorCandidate(
            test_id="search-submit",
            tag_name="button",
            editable=False,
        ),
        LocatorCandidate(
            test_id="product-card-name",
            tag_name="h2",
            editable=False,
        ),
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.status is CandidateSelectionStatus.SELECTED
    assert selection.candidate is not None
    assert selection.candidate.test_id == "catalog-search-input"
    assert selection.score is not None
    assert selection.score >= 0.60
    assert selection.candidate_count == 1
    assert selection.shortlist == ()


def test_fill_reports_no_candidates_when_similar_element_is_not_editable() -> None:
    candidates = [
        LocatorCandidate(
            test_id="catalog-search-input",
            tag_name="div",
            editable=False,
        )
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.status is CandidateSelectionStatus.NO_CANDIDATES
    assert selection.candidate is None
    assert selection.candidate_count == 0
    assert selection.shortlist == ()


def test_selection_reports_below_threshold_without_shortlist() -> None:
    candidates = [
        LocatorCandidate(
            test_id="billing-reference",
            tag_name="input",
            editable=True,
        )
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.status is CandidateSelectionStatus.BELOW_THRESHOLD
    assert selection.candidate is None
    assert selection.score is not None
    assert selection.score < 0.60
    assert selection.candidate_count == 1
    assert selection.shortlist == ()


def test_below_threshold_candidate_does_not_create_ambiguity() -> None:
    candidates = [
        LocatorCandidate(
            test_id="catalog-search-input",
            tag_name="input",
            editable=True,
        ),
        LocatorCandidate(
            test_id="billing-reference",
            tag_name="input",
            editable=True,
        ),
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.status is CandidateSelectionStatus.SELECTED
    assert selection.candidate is not None
    assert selection.candidate.test_id == "catalog-search-input"
    assert selection.candidate_count == 2
    assert selection.shortlist == ()


def test_selection_reports_bounded_two_candidate_ambiguity() -> None:
    candidates = [
        LocatorCandidate(
            test_id="catalog-search-input",
            tag_name="input",
            editable=True,
        ),
        LocatorCandidate(
            test_id="global-search-input",
            tag_name="input",
            editable=True,
        ),
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.status is CandidateSelectionStatus.AMBIGUOUS
    assert selection.candidate is None
    assert selection.candidate_count == 2
    assert tuple(candidate.test_id for candidate in selection.shortlist) == (
        "global-search-input",
        "catalog-search-input",
    )


def test_selection_reports_bounded_three_candidate_ambiguity() -> None:
    candidates = [
        LocatorCandidate(test_id="catalog-search-input", tag_name="input", editable=True),
        LocatorCandidate(test_id="global-search-input", tag_name="input", editable=True),
        LocatorCandidate(test_id="header-search-input", tag_name="input", editable=True),
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.status is CandidateSelectionStatus.AMBIGUOUS
    assert selection.candidate is None
    assert selection.candidate_count == 3
    assert len(selection.shortlist) == 3
    assert {candidate.test_id for candidate in selection.shortlist} == {
        "catalog-search-input",
        "global-search-input",
        "header-search-input",
    }


def test_selection_refuses_ambiguity_that_is_too_broad_for_fallback() -> None:
    candidates = [
        LocatorCandidate(test_id="catalog-search-input", tag_name="input", editable=True),
        LocatorCandidate(test_id="global-search-input", tag_name="input", editable=True),
        LocatorCandidate(test_id="header-search-input", tag_name="input", editable=True),
        LocatorCandidate(test_id="site-search-input", tag_name="input", editable=True),
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.status is CandidateSelectionStatus.AMBIGUOUS_TOO_BROAD
    assert selection.candidate is None
    assert selection.candidate_count == 4
    assert selection.shortlist == ()


def test_selection_rejects_invalid_ambiguity_bound() -> None:
    candidates = [
        LocatorCandidate(test_id="catalog-search-input", tag_name="input", editable=True),
        LocatorCandidate(test_id="global-search-input", tag_name="input", editable=True),
    ]

    with pytest.raises(ValueError, match="at least 2"):
        select_candidate(
            "search-input",
            RepairAction.FILL,
            candidates,
            maximum_ambiguity_candidates=1,
        )


def test_click_accepts_semantically_clickable_candidate() -> None:
    candidates = [
        LocatorCandidate(
            test_id="catalog-search-submit",
            tag_name="button",
        )
    ]

    selection = select_candidate("search-submit", RepairAction.CLICK, candidates)

    assert selection.status is CandidateSelectionStatus.SELECTED
    assert selection.candidate is not None
    assert selection.candidate.test_id == "catalog-search-submit"
