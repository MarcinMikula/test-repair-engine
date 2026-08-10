"""Unit tests for deterministic locator candidate selection."""

import pytest

from test_repair_engine.candidate_finder import (
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

    assert selection.candidate is not None
    assert selection.candidate.test_id == "catalog-search-input"
    assert selection.score is not None
    assert selection.score >= 0.60
    assert selection.candidate_count == 1


def test_fill_ignores_similar_non_editable_candidate() -> None:
    candidates = [
        LocatorCandidate(
            test_id="catalog-search-input",
            tag_name="div",
            editable=False,
        )
    ]

    selection = select_candidate("search-input", RepairAction.FILL, candidates)

    assert selection.candidate is None
    assert selection.candidate_count == 0


def test_selection_abstains_when_top_candidates_are_ambiguous() -> None:
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

    assert selection.candidate is None
    assert selection.candidate_count == 2
    assert "too close" in selection.reason


def test_click_accepts_semantically_clickable_candidate() -> None:
    candidates = [
        LocatorCandidate(
            test_id="catalog-search-submit",
            tag_name="button",
        )
    ]

    selection = select_candidate("search-submit", RepairAction.CLICK, candidates)

    assert selection.candidate is not None
    assert selection.candidate.test_id == "catalog-search-submit"
