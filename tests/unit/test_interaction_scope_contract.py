"""Fail-before contract tests for explicit Playwright interaction scope."""

from __future__ import annotations

from typing import get_args, get_type_hints

from playwright.sync_api import Frame, FrameLocator, Page

from test_repair_engine import playwright_adapter


def test_adapter_declares_bounded_playwright_interaction_scope() -> None:
    scope_type = getattr(
        playwright_adapter,
        "PlaywrightInteractionScope",
        None,
    )

    assert scope_type is not None, (
        "S9.3/S9.4/S9.5 validated Page, Frame, and FrameLocator as bounded "
        "interaction scopes, but the adapter does not declare that contract."
    )

    assert set(get_args(scope_type)) == {
        Page,
        Frame,
        FrameLocator,
    }


def test_current_recovery_entrypoints_use_declared_interaction_scope() -> None:
    scope_type = getattr(
        playwright_adapter,
        "PlaywrightInteractionScope",
        None,
    )

    assert scope_type is not None

    test_id_hints = get_type_hints(playwright_adapter.recover_test_id_action)
    role_link_hints = get_type_hints(playwright_adapter.recover_role_link_click)

    assert test_id_hints["page"] == scope_type
    assert role_link_hints["page"] == scope_type
