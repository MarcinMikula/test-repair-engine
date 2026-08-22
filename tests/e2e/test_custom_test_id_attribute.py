"""Regression seam for externally observed custom Playwright test-id semantics."""

from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from test_repair_engine.contracts import RepairAction
from test_repair_engine.playwright_adapter import recover_test_id_action
from test_repair_engine.runtime import (
    configure_runtime,
    reset_runtime,
    set_current_test_node,
)

pytestmark = pytest.mark.e2e


HTML_WITH_REAL_DRIFT_PATTERN = """
<!doctype html>
<html lang="en">
  <body>
    <label for="account_name">Account name</label>
    <input
      id="account_name"
      data-test="account_name"
      type="text"
      value=""
    />
  </body>
</html>
"""


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    reset_runtime()
    yield
    reset_runtime()


def test_custom_playwright_test_id_attribute_recovers_qualified_fill_drift(
    tmp_path: Path,
) -> None:
    node_id = (
        "tests/e2e/test_custom_test_id_attribute.py"
        "::test_custom_playwright_test_id_attribute_recovers_qualified_fill_drift"
    )

    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
    )
    set_current_test_node(node_id)

    with sync_playwright() as playwright:
        playwright.selectors.set_test_id_attribute("data-test")

        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML_WITH_REAL_DRIFT_PATTERN)

        with pytest.raises(PlaywrightTimeoutError):
            page.get_by_test_id("account-name").fill(
                "Jane Doe",
                timeout=150,
            )

        recovered = recover_test_id_action(
            page,
            action=RepairAction.FILL,
            original_test_id="account-name",
            retry=lambda replacement: page.get_by_test_id(replacement).fill(
                "Jane Doe"
            ),
            test_id_attribute="data-test",
            page_object="CheckoutPaymentPage",
            method_name="fill_account_name",
        )

        assert recovered is True
        assert (
            page.get_by_test_id("account_name").input_value()
            == "Jane Doe"
        )

        browser.close()
