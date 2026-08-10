"""Deterministic candidate scoring for bounded locator-drift recovery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from test_repair_engine.contracts import RepairAction

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_CLICK_TAGS = {"a", "button", "input", "summary"}
_CLICK_ROLES = {
    "button",
    "checkbox",
    "link",
    "menuitem",
    "radio",
    "switch",
    "tab",
}


@dataclass(frozen=True, slots=True)
class LocatorCandidate:
    """Bounded structural metadata for one data-testid candidate."""

    test_id: str
    tag_name: str
    role: str | None = None
    visible: bool = True
    enabled: bool = True
    editable: bool = False


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    """One action-compatible candidate with a deterministic similarity score."""

    candidate: LocatorCandidate
    score: float


@dataclass(frozen=True, slots=True)
class CandidateSelection:
    """Result of deterministic candidate selection."""

    candidate: LocatorCandidate | None
    score: float | None
    candidate_count: int
    reason: str


def tokenize_locator(value: str) -> tuple[str, ...]:
    """Normalize a locator value into stable lowercase alphanumeric tokens."""

    return tuple(_TOKEN_PATTERN.findall(value.lower()))


def candidate_supports_action(candidate: LocatorCandidate, action: RepairAction) -> bool:
    """Return whether bounded structural evidence supports the requested action."""

    if not candidate.visible or not candidate.enabled:
        return False

    tag_name = candidate.tag_name.lower()
    role = candidate.role.lower() if candidate.role else None

    if action is RepairAction.FILL:
        return candidate.editable

    if action is RepairAction.CLICK:
        return tag_name in _CLICK_TAGS or role in _CLICK_ROLES

    return False


def score_test_id(original_test_id: str, candidate_test_id: str) -> float:
    """Score candidate similarity using token overlap plus sequence similarity."""

    original_tokens = set(tokenize_locator(original_test_id))
    candidate_tokens = set(tokenize_locator(candidate_test_id))

    if not original_tokens or not candidate_tokens:
        return 0.0

    union = original_tokens | candidate_tokens
    overlap = original_tokens & candidate_tokens
    jaccard = len(overlap) / len(union)
    sequence = SequenceMatcher(None, original_test_id.lower(), candidate_test_id.lower()).ratio()

    subset_bonus = 0.10 if original_tokens < candidate_tokens else 0.0
    score = (0.70 * jaccard) + (0.30 * sequence) + subset_bonus
    return round(min(score, 1.0), 6)


def rank_candidates(
    original_test_id: str,
    action: RepairAction,
    candidates: list[LocatorCandidate],
) -> list[ScoredCandidate]:
    """Return compatible candidates ordered from strongest to weakest."""

    scored = [
        ScoredCandidate(
            candidate=candidate,
            score=score_test_id(original_test_id, candidate.test_id),
        )
        for candidate in candidates
        if candidate.test_id != original_test_id and candidate_supports_action(candidate, action)
    ]
    return sorted(scored, key=lambda item: (-item.score, item.candidate.test_id))


def select_candidate(
    original_test_id: str,
    action: RepairAction,
    candidates: list[LocatorCandidate],
    *,
    minimum_score: float = 0.60,
    minimum_margin: float = 0.15,
) -> CandidateSelection:
    """Select one unique bounded candidate or abstain on weak/ambiguous evidence."""

    ranked = rank_candidates(original_test_id, action, candidates)
    candidate_count = len(ranked)

    if not ranked:
        return CandidateSelection(
            candidate=None,
            score=None,
            candidate_count=0,
            reason="No action-compatible data-testid candidates were found.",
        )

    best = ranked[0]
    if best.score < minimum_score:
        return CandidateSelection(
            candidate=None,
            score=best.score,
            candidate_count=candidate_count,
            reason="Best candidate score is below the deterministic threshold.",
        )

    if len(ranked) > 1:
        margin = best.score - ranked[1].score
        if margin < minimum_margin:
            return CandidateSelection(
                candidate=None,
                score=best.score,
                candidate_count=candidate_count,
                reason="Top candidates are too close for deterministic selection.",
            )

    return CandidateSelection(
        candidate=best.candidate,
        score=best.score,
        candidate_count=candidate_count,
        reason="Unique deterministic candidate selected.",
    )
