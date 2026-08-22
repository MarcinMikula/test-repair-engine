"""Unit tests for the Playwright adapter without starting a browser."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError

import test_repair_engine.playwright_adapter as adapter_module
from test_repair_engine.contracts import (
    LLMEvidenceOutcome,
    RepairAction,
    RepairMethod,
    RepairOutcome,
    RepairRecord,
)
from test_repair_engine.ollama_provider import (
    OllamaDecisionOutcome,
    OllamaDecisionResult,
)
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
        editable_error: bool = False,
        test_id_attribute: str = "data-testid",
    ) -> None:
        self.test_id = test_id
        self.test_id_attribute = test_id_attribute
        self.tag_name = tag_name
        self.role = role
        self.visible = visible
        self.enabled = enabled
        self.editable = editable
        self.editable_error = editable_error

    def get_attribute(self, name: str) -> str | None:
        if name == self.test_id_attribute:
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
        if self.editable_error:
            raise PlaywrightError("Element type does not support editability.")
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


class StubOllamaProvider:
    instances: list[StubOllamaProvider] = []
    decision = OllamaDecisionResult(outcome=OllamaDecisionOutcome.ABSTAINED)

    def __init__(self, *, model: str, timeout_seconds: float) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.calls: list[dict[str, object]] = []
        type(self).instances.append(self)

    def decide(self, **kwargs: object) -> OllamaDecisionResult:
        self.calls.append(kwargs)
        return type(self).decision


@pytest.fixture(autouse=True)
def clean_runtime() -> None:
    reset_runtime()
    yield
    reset_runtime()


def _ambiguity_page() -> FakePage:
    return FakePage(
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


def _install_provider(
    monkeypatch: pytest.MonkeyPatch,
    decision: OllamaDecisionResult,
) -> None:
    StubOllamaProvider.instances = []
    StubOllamaProvider.decision = decision
    monkeypatch.setattr(adapter_module, "OllamaProvider", StubOllamaProvider)


def _finalized_record(tmp_path: Path, node_id: str) -> RepairRecord:
    written = finalize_test(node_id)
    assert len(written) == 1
    return load_repair_record(written[0])


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

    record = _finalized_record(tmp_path, node_id)
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


def test_collector_uses_explicit_custom_test_id_attribute() -> None:
    page = FakePage(
        [
            FakeElement(
                test_id="account_name",
                test_id_attribute="data-test",
                tag_name="input",
                editable=True,
            ),
        ]
    )

    candidates = adapter_module.collect_test_id_candidates(
        page,
        test_id_attribute="data-test",
    )

    assert page.locator_calls == ["[data-test]"]
    assert len(candidates) == 1
    assert candidates[0].test_id == "account_name"
    assert candidates[0].editable is True


def test_adapter_keeps_click_candidate_when_editability_probe_is_not_applicable(
    tmp_path: Path,
) -> None:
    node_id = "tests/e2e/test_login.py::test_login"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)
    page = FakePage(
        [
            FakeElement(
                test_id="btn-login-a1b2",
                tag_name="button",
                editable_error=True,
            ),
            FakeElement(
                test_id="btn-add-item-c3d4",
                tag_name="button",
                editable_error=True,
            ),
        ]
    )
    retried_with: list[str] = []

    candidates = adapter_module.collect_test_id_candidates(page)

    assert [(candidate.test_id, candidate.editable) for candidate in candidates] == [
        ("btn-login-a1b2", False),
        ("btn-add-item-c3d4", False),
    ]

    recovered = recover_test_id_action(
        page,
        action=RepairAction.CLICK,
        original_test_id="btn-login",
        retry=retried_with.append,
    )

    assert recovered is True
    assert retried_with == ["btn-login-a1b2"]

    record = _finalized_record(tmp_path, node_id)
    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.repair_method is RepairMethod.HEURISTIC
    assert record.replacement_locator == "btn-login-a1b2"
    assert record.selected_score is not None
    assert record.selected_score >= 0.60
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is False
    assert record.llm_evidence.eligible is False
    assert record.llm_evidence.call_attempted is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


def test_deterministic_winner_never_calls_llm_even_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider(
        monkeypatch,
        OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
            selected_test_id="catalog-search-input",
        ),
    )
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
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
    )

    assert recovered is True
    assert retried_with == ["catalog-search-input"]
    assert StubOllamaProvider.instances == []

    record = _finalized_record(tmp_path, node_id)
    assert record.repair_method is RepairMethod.HEURISTIC
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is True
    assert record.llm_evidence.eligible is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


def test_ambiguity_with_llm_disabled_stays_fail_closed_without_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider(
        monkeypatch,
        OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
            selected_test_id="catalog-search-input",
        ),
    )
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(enabled=True, output_dir=tmp_path)
    set_current_test_node(node_id)
    retried_with: list[str] = []

    recovered = recover_test_id_action(
        _ambiguity_page(),
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=retried_with.append,
    )

    assert recovered is False
    assert retried_with == []
    assert StubOllamaProvider.instances == []

    record = _finalized_record(tmp_path, node_id)
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is False
    assert record.llm_evidence.eligible is True
    assert record.llm_evidence.call_attempted is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


def test_validated_llm_selection_gets_one_call_and_one_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider(
        monkeypatch,
        OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
            selected_test_id="catalog-search-input",
        ),
    )
    clock = iter([1_000_000, 6_000_000])
    monkeypatch.setattr(adapter_module, "perf_counter_ns", clock.__next__)
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
        llm_timeout_seconds=12.5,
    )
    set_current_test_node(node_id)
    retried_with: list[str] = []

    recovered = recover_test_id_action(
        _ambiguity_page(),
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=retried_with.append,
        page_object="EcommerceSearchPage",
        method_name="fill_by_test_id",
    )

    assert recovered is True
    assert retried_with == ["catalog-search-input"]
    assert len(StubOllamaProvider.instances) == 1
    provider = StubOllamaProvider.instances[0]
    assert provider.model == "qwen2.5-coder:7b"
    assert provider.timeout_seconds == 12.5
    assert len(provider.calls) == 1
    assert provider.calls[0]["original_test_id"] == "search-input"
    assert provider.calls[0]["page_object"] == "EcommerceSearchPage"
    assert provider.calls[0]["method_name"] == "fill_by_test_id"

    record = _finalized_record(tmp_path, node_id)
    assert record.runtime_result is RepairOutcome.RECOVERED
    assert record.repair_method is RepairMethod.LLM
    assert record.replacement_locator == "catalog-search-input"
    assert record.selected_score is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.VALIDATED_SELECTION
    assert record.llm_evidence.call_attempted is True
    assert record.llm_evidence.response_received is True
    assert record.llm_evidence.latency_ms == 5


@pytest.mark.parametrize(
    ("provider_outcome", "evidence_outcome", "response_received"),
    [
        (
            OllamaDecisionOutcome.CALL_FAILED,
            LLMEvidenceOutcome.CALL_FAILED,
            False,
        ),
        (
            OllamaDecisionOutcome.TIMEOUT,
            LLMEvidenceOutcome.TIMEOUT,
            False,
        ),
        (
            OllamaDecisionOutcome.INVALID_JSON,
            LLMEvidenceOutcome.INVALID_JSON,
            True,
        ),
        (
            OllamaDecisionOutcome.INVALID_SCHEMA,
            LLMEvidenceOutcome.INVALID_SCHEMA,
            True,
        ),
        (
            OllamaDecisionOutcome.ABSTAINED,
            LLMEvidenceOutcome.ABSTAINED,
            True,
        ),
        (
            OllamaDecisionOutcome.OUTSIDE_ALLOWLIST,
            LLMEvidenceOutcome.OUTSIDE_ALLOWLIST,
            True,
        ),
    ],
)
def test_non_selection_provider_outcomes_never_retry_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider_outcome: OllamaDecisionOutcome,
    evidence_outcome: LLMEvidenceOutcome,
    response_received: bool,
) -> None:
    _install_provider(
        monkeypatch,
        OllamaDecisionResult(
            outcome=provider_outcome,
            reason="Provider did not authorize a selection.",
        ),
    )
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
    )
    set_current_test_node(node_id)
    retried_with: list[str] = []

    recovered = recover_test_id_action(
        _ambiguity_page(),
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=retried_with.append,
    )

    assert recovered is False
    assert retried_with == []
    assert len(StubOllamaProvider.instances) == 1
    assert len(StubOllamaProvider.instances[0].calls) == 1

    record = _finalized_record(tmp_path, node_id)
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.replacement_locator is None
    assert record.repair_method is None
    assert record.selected_score is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.outcome is evidence_outcome
    assert record.llm_evidence.call_attempted is True
    assert record.llm_evidence.response_received is response_received


def test_execution_allowlist_rejects_inconsistent_validated_provider_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider(
        monkeypatch,
        OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
            selected_test_id="invented-search-input",
        ),
    )
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
    )
    set_current_test_node(node_id)
    retried_with: list[str] = []

    recovered = recover_test_id_action(
        _ambiguity_page(),
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=retried_with.append,
    )

    assert recovered is False
    assert retried_with == []

    record = _finalized_record(tmp_path, node_id)
    assert record.replacement_locator is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.OUTSIDE_ALLOWLIST
    assert record.llm_evidence.response_received is True
    assert "invented-search-input" not in (record.reason or "")


def test_validated_llm_retry_failure_is_not_retried_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider(
        monkeypatch,
        OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
            selected_test_id="catalog-search-input",
        ),
    )
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
    )
    set_current_test_node(node_id)
    retried_with: list[str] = []

    def fail_retry(replacement_test_id: str) -> None:
        retried_with.append(replacement_test_id)
        raise PlaywrightError("Selected replacement still fails.")

    recovered = recover_test_id_action(
        _ambiguity_page(),
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=fail_retry,
    )

    assert recovered is False
    assert retried_with == ["catalog-search-input"]
    assert len(StubOllamaProvider.instances) == 1
    assert len(StubOllamaProvider.instances[0].calls) == 1

    record = _finalized_record(tmp_path, node_id)
    assert record.runtime_result is RepairOutcome.FAILED
    assert record.repair_method is RepairMethod.LLM
    assert record.replacement_locator == "catalog-search-input"
    assert record.selected_score is None
    assert record.llm_evidence is not None
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.VALIDATED_SELECTION


def test_too_broad_ambiguity_never_calls_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider(
        monkeypatch,
        OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
            selected_test_id="a-search-input",
        ),
    )
    node_id = "tests/e2e/test_search.py::test_product_search"
    configure_runtime(
        enabled=True,
        output_dir=tmp_path,
        llm_enabled=True,
        llm_model="qwen2.5-coder:7b",
    )
    set_current_test_node(node_id)
    page = FakePage(
        [
            FakeElement(
                test_id=f"{prefix}-search-input",
                tag_name="input",
                editable=True,
            )
            for prefix in ("a", "b", "c", "d")
        ]
    )

    recovered = recover_test_id_action(
        page,
        action=RepairAction.FILL,
        original_test_id="search-input",
        retry=lambda replacement: None,
    )

    assert recovered is False
    assert StubOllamaProvider.instances == []

    record = _finalized_record(tmp_path, node_id)
    assert record.llm_evidence is not None
    assert record.llm_evidence.enabled is True
    assert record.llm_evidence.eligible is False
    assert record.llm_evidence.outcome is LLMEvidenceOutcome.NOT_CALLED


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
