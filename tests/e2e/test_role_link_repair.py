"""Regression coverage for the qualified ROLE=link + CLICK repair authority."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import sync_playwright

import test_repair_engine.playwright_adapter as adapter_module
from test_repair_engine.contracts import (
    LLMEvidenceOutcome,
    LocatorKind,
    RepairMethod,
    RepairOutcome,
)
from test_repair_engine.recording import load_repair_record
from test_repair_engine.runtime import (
    configure_runtime,
    finalize_test,
    reset_runtime,
    set_current_test_node,
)

pytestmark = pytest.mark.e2e

ORIGINAL_NAME = "Belt Sander Belt Sander $73.59"
EXPANDED_NAME = "Belt Sander Compare Belt Sander CO2 A B C D E $73.59"


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    reset_runtime()
    yield
    reset_runtime()


def _role_locator_kind() -> LocatorKind:
    return LocatorKind("role_link")


def _recover_role_link_click(
    page: Any,
    *,
    original_accessible_name: str,
    retry: Any,
    page_object: str | None = None,
    method_name: str | None = None,
) -> bool:
    recover = getattr(
        adapter_module,
        "recover_role_link_click",
        None,
    )
    assert callable(recover), (
        "Qualified S8.3b authority requires playwright_adapter.recover_role_link_click()."
    )
    return recover(
        page,
        original_accessible_name=original_accessible_name,
        retry=retry,
        page_object=page_object,
        method_name=method_name,
    )


def _finalized_record(tmp_path: Path, node_id: str):
    written = finalize_test(node_id)
    assert len(written) == 1
    return load_repair_record(written[0])


def test_role_locator_kind_contract_is_available() -> None:
    assert _role_locator_kind() is LocatorKind.ROLE_LINK


def test_role_link_repair_recovers_unique_insertion_expansion(
    tmp_path: Path,
) -> None:
    node_id = (
        "tests/e2e/test_role_link_repair.py::"
        "test_role_link_repair_recovers_unique_insertion_expansion"
    )
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
    )
    set_current_test_node(node_id)

    html = f"""
    <main>
      <a
        href="#product"
        aria-label="{EXPANDED_NAME}"
        onclick="document.body.dataset.clicked='yes'"
      >candidate</a>
    </main>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)

        assert (
            page.get_by_role(
                "link",
                name=ORIGINAL_NAME,
                exact=True,
            ).count()
            == 0
        )

        recovered = _recover_role_link_click(
            page,
            original_accessible_name=ORIGINAL_NAME,
            retry=lambda replacement: page.get_by_role(
                "link",
                name=replacement,
            ).click(),
            page_object="CatalogPage",
            method_name="open_product",
        )

        assert recovered is True
        assert page.locator("body").get_attribute("data-clicked") == "yes"
        browser.close()

    record = _finalized_record(tmp_path, node_id)
    assert record.locator_kind is _role_locator_kind()
    assert record.original_locator == ORIGINAL_NAME
    assert record.replacement_locator is not None
    assert record.replacement_locator.startswith("^")
    assert record.replacement_locator.endswith("$")
    assert record.repair_method is RepairMethod.HEURISTIC
    assert record.candidate_count == 1
    assert record.selected_score is None
    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is True
    assert record.llm_evidence.eligible is False
    assert record.llm_evidence.call_attempted is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


def test_role_link_repair_fails_closed_when_no_insertion_candidate(
    tmp_path: Path,
) -> None:
    node_id = (
        "tests/e2e/test_role_link_repair.py::"
        "test_role_link_repair_fails_closed_when_no_insertion_candidate"
    )
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    html = """
    <main>
      <a
        href="#other"
        aria-label="Circular Saw Compare Circular Saw CO2 A B C D E $80.19"
      >other</a>
    </main>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        retried: list[object] = []

        recovered = _recover_role_link_click(
            page,
            original_accessible_name=ORIGINAL_NAME,
            retry=retried.append,
        )

        assert recovered is False
        assert retried == []
        browser.close()

    record = _finalized_record(tmp_path, node_id)
    assert record.locator_kind is _role_locator_kind()
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.candidate_count == 0


def test_role_link_repair_fails_closed_on_ambiguity(
    tmp_path: Path,
) -> None:
    node_id = "tests/e2e/test_role_link_repair.py::test_role_link_repair_fails_closed_on_ambiguity"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    html = f"""
    <main>
      <a href="#one" aria-label="{EXPANDED_NAME}">one</a>
      <a
        href="#two"
        aria-label="Belt Sander Featured Belt Sander $73.59"
      >two</a>
    </main>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        retried: list[object] = []

        recovered = _recover_role_link_click(
            page,
            original_accessible_name=ORIGINAL_NAME,
            retry=retried.append,
        )

        assert recovered is False
        assert retried == []
        browser.close()

    record = _finalized_record(tmp_path, node_id)
    assert record.locator_kind is _role_locator_kind()
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.candidate_count == 2


def test_role_link_repair_fails_closed_when_unique_candidate_is_disabled(
    tmp_path: Path,
) -> None:
    node_id = (
        "tests/e2e/test_role_link_repair.py::"
        "test_role_link_repair_fails_closed_when_unique_candidate_is_disabled"
    )
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    html = f"""
    <main>
      <a
        href="#product"
        aria-label="{EXPANDED_NAME}"
        aria-disabled="true"
      >candidate</a>
    </main>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        retried: list[object] = []

        recovered = _recover_role_link_click(
            page,
            original_accessible_name=ORIGINAL_NAME,
            retry=retried.append,
        )

        assert recovered is False
        assert retried == []
        browser.close()

    record = _finalized_record(tmp_path, node_id)
    assert record.locator_kind is _role_locator_kind()
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.candidate_count == 1


def test_role_link_repair_fails_closed_when_original_exact_name_still_resolves(
    tmp_path: Path,
) -> None:
    node_id = (
        "tests/e2e/test_role_link_repair.py::"
        "test_role_link_repair_fails_closed_when_original_exact_name_still_resolves"
    )
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    html = f"""
    <main>
      <a
        href="#original"
        aria-label="{ORIGINAL_NAME}"
        aria-disabled="true"
      >original</a>
      <a href="#replacement" aria-label="{EXPANDED_NAME}">
        replacement
      </a>
    </main>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        retried: list[object] = []

        assert (
            page.get_by_role(
                "link",
                name=ORIGINAL_NAME,
                exact=True,
            ).count()
            == 1
        )

        recovered = _recover_role_link_click(
            page,
            original_accessible_name=ORIGINAL_NAME,
            retry=retried.append,
        )

        assert recovered is False
        assert retried == []
        browser.close()

    record = _finalized_record(tmp_path, node_id)
    assert record.locator_kind is _role_locator_kind()
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.candidate_count == 0


@pytest.mark.parametrize(
    ("candidate_name", "case_id"),
    [
        (
            "Belt Sander Compare Belt Sander CO2 A B C D E $74.59",
            "wrong_price",
        ),
        (
            "Special Belt Sander Compare Belt Sander $73.59",
            "prefix_insertion",
        ),
        (
            "Belt Sander Compare Belt Sander $73.59 Sale",
            "suffix_insertion",
        ),
        (
            "Belt Sander $73.59",
            "deletion",
        ),
        (
            "Belt Sander $73.59 Compare Belt Sander",
            "reorder",
        ),
        (
            "Mega Belt Sander Compare Belt Sander $73.59",
            "near_collision_prefix",
        ),
    ],
)
def test_role_link_repair_rejects_out_of_authority_name_changes(
    tmp_path: Path,
    candidate_name: str,
    case_id: str,
) -> None:
    node_id = (
        "tests/e2e/test_role_link_repair.py::"
        f"test_role_link_repair_rejects_out_of_authority_name_changes[{case_id}]"
    )
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    html = f"""
    <main>
      <a href="#candidate" aria-label="{candidate_name}">
        candidate
      </a>
    </main>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        retried: list[object] = []

        assert (
            page.get_by_role(
                "link",
                name=ORIGINAL_NAME,
                exact=True,
            ).count()
            == 0
        )

        recovered = _recover_role_link_click(
            page,
            original_accessible_name=ORIGINAL_NAME,
            retry=retried.append,
        )

        assert recovered is False
        assert retried == []
        browser.close()

    record = _finalized_record(tmp_path, node_id)
    assert record.locator_kind is _role_locator_kind()
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.candidate_count == 0
