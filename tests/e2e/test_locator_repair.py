"""Real-browser proof for the first deterministic locator-drift repair slice."""

from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from test_repair_engine.contracts import RepairAction, RepairOutcome
from test_repair_engine.contracts import TestOutcome as RepairTestOutcome
from test_repair_engine.playwright_adapter import recover_test_id_action
from test_repair_engine.recording import load_repair_record
from test_repair_engine.runtime import (
    configure_runtime,
    finalize_test,
    reset_runtime,
    set_current_test_node,
)

pytestmark = pytest.mark.e2e


HTML_WITH_DRIFT = """
<!doctype html>
<html lang="en">
  <body>
    <label for="catalog-search-input">Search</label>
    <input
      id="catalog-search-input"
      data-testid="catalog-search-input"
      name="q"
      value=""
    />
    <button data-testid="search-submit" type="button">Search</button>
  </body>
</html>
"""


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    reset_runtime()
    yield
    reset_runtime()


def test_original_locator_fails_after_controlled_data_testid_drift() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML_WITH_DRIFT)

        with pytest.raises(PlaywrightTimeoutError):
            page.get_by_test_id("search-input").fill("Samsung 65 OLED", timeout=150)

        browser.close()


def test_deterministic_repair_recovers_fill_and_persists_validated_record(
    tmp_path: Path,
) -> None:
    node_id = "tests/e2e/test_locator_repair.py::test_repaired_search_input"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML_WITH_DRIFT)

        recovered = recover_test_id_action(
            page,
            action=RepairAction.FILL,
            original_test_id="search-input",
            retry=lambda replacement: page.get_by_test_id(replacement).fill("Samsung 65 OLED"),
            page_object="EcommerceSearchPage",
            method_name="search_for",
        )

        assert recovered is True
        assert page.get_by_test_id("catalog-search-input").input_value() == "Samsung 65 OLED"
        browser.close()

    written = finalize_test(node_id)
    assert len(written) == 1

    record = load_repair_record(written[0])
    assert record.original_locator == "search-input"
    assert record.replacement_locator == "catalog-search-input"
    assert record.page_object == "EcommerceSearchPage"
    assert record.method_name == "search_for"
    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.test_result is RepairTestOutcome.PASSED
