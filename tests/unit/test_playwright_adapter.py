"""Unit tests for the Playwright adapter without starting a browser."""

from pathlib import Path

import pytest

from test_repair_engine.contracts import LLMEvidenceOutcome, RepairAction, RepairOutcome
from test_repair_engine.playwright_adapter import recover_test_id_action
from test_repair_engine.recording import load_repair_record
from test_repair_engine.runtime import (
    configure_runtime,
    finalize_test,
    reset_runtime,
    set_current_test_node,
)

pytestmark = pytest.mark.unit


class FakeElement:
    def __init__(
        self,
        *,
        test_id: str,
        tag_name: str,
        role: str | None = None,
        visible: bool = True,
        enabled: bool = True,
        editable: bool = False,
    ) -> None:
        self.test_id = test_id
        self.tag_name = tag_name
        self.role = role
        self.visible = visible
        self.enabled = enabled
        self.editable = editable

    def get_attribute(self, name: str) -> str | None:
        if name == "data-testid":
            return self.test_id
        if name == "role":
            return self.role
        return None

    def evaluate(self, expression: str) -> str:
        assert "tagName" in expression
        return self.tag_name

    def is_visible(self) -> bool:
        return self.visible

    def is_enabled(self) -> bool:
        return self.enabled

    def is_editable(self) -> bool:
        return self.editable


class FakeLocatorCollection:
    def __init__(self, elements: list[FakeElement]) -> None:
        self.elements = elements

    def count(self) -> int:
        return len(self.elements)

    def nth(self, index: int) -> FakeElement:
        return self.elements[index]


class FakePage:
    def __init__(self, elements: list[FakeElement]) -> None:
        self.elements = elements
        self.locator_calls: list[str] = []

    def locator(self, selector: str) -> FakeLocatorCollection:
        self.locator_calls.append(selector)
        return FakeLocatorCollection(self.elements)


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    reset_runtime()
    yield
    reset_runtime()


def test_adapter_recovers_unique_fill_candidate_and_registers_record(tmp_path: Path) -> None:
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)
    page = FakePage(
        [
            FakeElement(
                test_id="catalog-search-input",
                tag_name="input",
                editable=True,
            ),
            FakeElement(
                test_id="search-submit",
                tag_name="button",
            ),
        ]
    )
    retried_with: list[str] = []

    recovered = recover_test_id_action(
        page,
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=retried_with.append,
        page_object="EcommerceSearchPage",
        method_name="search_for",
    )

    assert recovered is True
    assert retried_with == ["catalog-search-input"]
    assert page.locator_calls == ["[data-testid]"]

    written = finalize_test(node_id)
    record = load_repair_record(written[0])
    assert record.schema_version == "0.2"
    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.original_locator == "search-input"
    assert record.replacement_locator == "catalog-search-input"
    assert record.page_object == "EcommerceSearchPage"
    assert record.method_name == "search_for"
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is False
    assert record.llm_evidence.eligible is False
    assert record.llm_evidence.call_attempted is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


@pytest.mark.parametrize("llm_enabled", [False, True])
def test_adapter_records_bounded_ambiguity_eligibility_without_calling_llm(
    tmp_path: Path,
    llm_enabled: bool,
) -> None:
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=llm_enabled,
        llm_model="qwen2.5-coder:7b" if llm_enabled else None,
    )
    set_current_test_node(node_id)
    page = FakePage(
        [
            FakeElement(
                test_id="catalog-search-input",
                tag_name="input",
                editable=True,
            ),
            FakeElement(
                test_id="global-search-input",
                tag_name="input",
                editable=True,
            ),
        ]
    )
    retried_with: list[str] = []

    recovered = recover_test_id_action(
        page,
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=retried_with.append,
    )

    assert recovered is False
    assert retried_with == []

    written = finalize_test(node_id)
    record = load_repair_record(written[0])
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is llm_enabled
    assert record.llm_evidence.eligible is True
    assert record.llm_evidence.call_attempted is False
    assert record.llm_evidence.response_received is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED
    assert record.llm_evidence.model == ("qwen2.5-coder:7b" if llm_enabled else None)


def test_adapter_is_noop_when_runtime_repair_is_disabled() -> None:
    page = FakePage(
        [
            FakeElement(
                test_id="catalog-search-input",
                tag_name="input",
                editable=True,
            )
        ]
    )

    recovered = recover_test_id_action(
        page,
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=lambda replacement: None,
    )

    assert recovered is False
    assert page.locator_calls == []
