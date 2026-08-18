"""Controlled real-browser proof for bounded LLM ambiguity recovery."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import test_repair_engine.playwright_adapter as adapter_module
from test_repair_engine.contracts import (
    LLMEvidenceOutcome,
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.contracts import TestOutcome as RepairTestOutcome
from test_repair_engine.ollama_provider import (
    OllamaDecisionOutcome,
    OllamaDecisionResult,
)
from test_repair_engine.playwright_adapter import recover_test_id_action
from test_repair_engine.recording import load_repair_record
from test_repair_engine.runtime import (
    configure_runtime,
    finalize_test,
    mark_test_failed,
    reset_runtime,
    set_current_test_node,
)

pytestmark = pytest.mark.e2e

BROKEN_TEST_ID = "search-input"
EXPECTED_REPLACEMENT_TEST_ID = "catalog-search-input"
OTHER_AMBIGUOUS_TEST_ID = "global-search-input"
SEARCH_VALUE = "hammer"

HTML_WITH_BOUNDED_AMBIGUITY = """
<!doctype html>
<html lang="en">
  <body>
    <label for="catalog-search-input">Catalog search</label>
    <input
      id="catalog-search-input"
      data-testid="catalog-search-input"
      name="catalog-q"
      value=""
    />

    <label for="global-search-input">Global search</label>
    <input
      id="global-search-input"
      data-testid="global-search-input"
      name="global-q"
      value=""
    />
  </body>
</html>
"""


class ControlledOllamaProvider:
    """Deterministic provider double used only to validate real browser wiring."""

    instances: list[ControlledOllamaProvider] = []

    def __init__(self, *, model: str, timeout_seconds: float) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.calls: list[dict[str, object]] = []
        type(self).instances.append(self)

    def decide(self, **kwargs: object) -> OllamaDecisionResult:
        self.calls.append(kwargs)
        return OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
            selected_test_id=EXPECTED_REPLACEMENT_TEST_ID,
        )


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    ControlledOllamaProvider.instances = []
    reset_runtime()
    yield
    reset_runtime()
    ControlledOllamaProvider.instances = []


def _assert_original_locator_fails(page: Page) -> None:
    with pytest.raises(PlaywrightTimeoutError):
        page.get_by_test_id(BROKEN_TEST_ID).fill(SEARCH_VALUE, timeout=150)


def _finalized_record(tmp_path: Path, node_id: str) -> RepairRecord:
    written = finalize_test(node_id)
    assert len(written) == 1
    return load_repair_record(written[0])


def test_controlled_ambiguity_original_locator_really_fails() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML_WITH_BOUNDED_AMBIGUITY)

        _assert_original_locator_fails(page)
        assert page.get_by_test_id(EXPECTED_REPLACEMENT_TEST_ID).input_value() == ""
        assert page.get_by_test_id(OTHER_AMBIGUOUS_TEST_ID).input_value() == ""

        browser.close()


def test_controlled_ambiguity_deterministic_only_stays_fail_closed(tmp_path: Path) -> None:
    node_id = "tests/e2e/test_llm_ambiguity_repair.py::test_controlled_ambiguity_deterministic_only"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML_WITH_BOUNDED_AMBIGUITY)

        _assert_original_locator_fails(page)

        recovered = recover_test_id_action(
            page,
            action=RepairAction.FILL,
            original_test_id=BROKEN_TEST_ID,
            retry=lambda replacement: page.get_by_test_id(replacement).fill(SEARCH_VALUE),
            page_object="ControlledSearchPage",
            method_name="fill_by_test_id",
        )

        assert recovered is False
        assert page.get_by_test_id(EXPECTED_REPLACEMENT_TEST_ID).input_value() == ""
        assert page.get_by_test_id(OTHER_AMBIGUOUS_TEST_ID).input_value() == ""

        browser.close()

    mark_test_failed(node_id)
    record = _finalized_record(tmp_path, node_id)
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.test_result is RepairTestOutcome.FAILED
    assert record.repair_method is None
    assert record.replacement_locator is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is False
    assert record.llm_evidence.eligible is True
    assert record.llm_evidence.call_attempted is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


def test_controlled_provider_recovers_real_browser_ambiguity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter_module, "OllamaProvider", ControlledOllamaProvider)

    node_id = (
        "tests/e2e/test_llm_ambiguity_repair.py::"
        "test_controlled_provider_recovers_real_browser_ambiguity"
    )
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="controlled-s2.5-provider",
        llm_timeout_seconds=5.0,
    )
    set_current_test_node(node_id)

    retry_calls: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML_WITH_BOUNDED_AMBIGUITY)

        _assert_original_locator_fails(page)

        def retry(replacement: str) -> None:
            retry_calls.append(replacement)
            page.get_by_test_id(replacement).fill(SEARCH_VALUE)

        recovered = recover_test_id_action(
            page,
            action=RepairAction.FILL,
            original_test_id=BROKEN_TEST_ID,
            retry=retry,
            page_object="ControlledSearchPage",
            method_name="fill_by_test_id",
        )

        assert recovered is True
        assert retry_calls == [EXPECTED_REPLACEMENT_TEST_ID]
        assert page.get_by_test_id(EXPECTED_REPLACEMENT_TEST_ID).input_value() == SEARCH_VALUE
        assert page.get_by_test_id(OTHER_AMBIGUOUS_TEST_ID).input_value() == ""

        browser.close()

    assert len(ControlledOllamaProvider.instances) == 1
    provider = ControlledOllamaProvider.instances[0]
    assert provider.model == "controlled-s2.5-provider"
    assert provider.timeout_seconds == 5.0
    assert len(provider.calls) == 1

    provider_call = provider.calls[0]
    shortlist = provider_call["shortlist"]
    assert isinstance(shortlist, tuple)
    assert {candidate.test_id for candidate in shortlist} == {
        EXPECTED_REPLACEMENT_TEST_ID,
        OTHER_AMBIGUOUS_TEST_ID,
    }
    assert provider_call["original_test_id"] == BROKEN_TEST_ID
    assert provider_call["action"] is RepairAction.FILL

    record = _finalized_record(tmp_path, node_id)
    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.test_result is RepairTestOutcome.PASSED
    assert record.repair_method is RepairMethod.LLM
    assert record.replacement_locator == EXPECTED_REPLACEMENT_TEST_ID
    assert record.selected_score is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is True
    assert record.llm_evidence.eligible is True
    assert record.llm_evidence.call_attempted is True
    assert record.llm_evidence.response_received is True
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.VALIDATED_SELECTION
    assert record.llm_evidence.model == "controlled-s2.5-provider"
