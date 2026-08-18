"""Unit tests for the isolated bounded Ollama decision contract."""

import json
from urllib.error import URLError

import pytest

from test_repair_engine.candidate_finder import LocatorCandidate
from test_repair_engine.contracts import RepairAction
from test_repair_engine.ollama_provider import (
    OllamaDecisionOutcome,
    OllamaProvider,
    build_decision_payload,
    build_decision_schema,
    parse_model_decision,
)

pytestmark = pytest.mark.unit


def _candidate(test_id: str, *, editable: bool = True) -> LocatorCandidate:
    return LocatorCandidate(test_id=test_id, tag_name="input", editable=editable)


def _shortlist() -> tuple[LocatorCandidate, ...]:
    # Deliberately reversed: provider payload must not leak deterministic rank order.
    return (_candidate("header-search-input"), _candidate("catalog-search-input"))


def _response(content: str) -> bytes:
    return json.dumps({"message": {"role": "assistant", "content": content}}).encode("utf-8")


class CapturingTransport:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.calls: list[tuple[str, bytes, float]] = []

    def __call__(self, url: str, body: bytes, timeout_seconds: float) -> bytes:
        self.calls.append((url, body, timeout_seconds))
        return self.response


def test_payload_exposes_exact_shortlist_contract_without_scores() -> None:
    shortlist = _shortlist()

    payload = build_decision_payload(
        model="qwen2.5-coder:7b",
        action=RepairAction.FILL,
        original_test_id="search-input",
        shortlist=shortlist,
        page_object="EcommerceSearchPage",
        method_name="fill_by_test_id",
    )

    schema = build_decision_schema(shortlist)
    assert payload["format"] == schema
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0, "seed": 42}

    user_context = json.loads(payload["messages"][1]["content"])
    assert user_context["response_schema"] == schema
    assert [item["test_id"] for item in user_context["candidates"]] == [
        "catalog-search-input",
        "header-search-input",
    ]
    assert all("score" not in item for item in user_context["candidates"])


def test_provider_makes_one_chat_call_and_returns_validated_selection() -> None:
    transport = CapturingTransport(
        _response('{"decision":"select","candidate_test_id":"catalog-search-input"}')
    )
    provider = OllamaProvider(
        model="qwen2.5-coder:7b",
        timeout_seconds=12.5,
        transport=transport,
    )

    result = provider.decide(
        action=RepairAction.FILL,
        original_test_id="search-input",
        shortlist=_shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.VALIDATED_SELECTION
    assert result.selected_test_id == "catalog-search-input"
    assert len(transport.calls) == 1
    url, body, timeout_seconds = transport.calls[0]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert timeout_seconds == 12.5
    assert json.loads(body)["model"] == "qwen2.5-coder:7b"


def test_parser_accepts_explicit_abstention() -> None:
    result = parse_model_decision(
        '{"decision":"abstain","candidate_test_id":null}',
        _shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.ABSTAINED
    assert result.selected_test_id is None


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        '{"decision":"select",',
        '{"decision":"abstain","decision":"select","candidate_test_id":null}',
    ],
)
def test_parser_rejects_invalid_or_ambiguous_json(content: str) -> None:
    result = parse_model_decision(content, _shortlist())

    assert result.outcome is OllamaDecisionOutcome.INVALID_JSON


@pytest.mark.parametrize(
    "content",
    [
        "{}",
        '{"decision":"select"}',
        '{"decision":"select","candidate_test_id":"catalog-search-input","extra":true}',
        '{"decision":"other","candidate_test_id":"catalog-search-input"}',
        '{"decision":"select","candidate_test_id":null}',
        '{"decision":"abstain","candidate_test_id":"catalog-search-input"}',
        "[]",
    ],
)
def test_parser_rejects_structured_contract_mismatches(content: str) -> None:
    result = parse_model_decision(content, _shortlist())

    assert result.outcome is OllamaDecisionOutcome.INVALID_SCHEMA


def test_parser_rejects_selection_outside_exact_allowlist() -> None:
    result = parse_model_decision(
        '{"decision":"select","candidate_test_id":"search-input-new"}',
        _shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.OUTSIDE_ALLOWLIST
    assert result.selected_test_id is None


def test_provider_classifies_timeout_without_retrying() -> None:
    calls = 0

    def timeout_transport(url: str, body: bytes, timeout_seconds: float) -> bytes:
        nonlocal calls
        calls += 1
        raise TimeoutError

    provider = OllamaProvider(
        model="qwen2.5-coder:7b",
        timeout_seconds=30,
        transport=timeout_transport,
    )
    result = provider.decide(
        action=RepairAction.FILL,
        original_test_id="search-input",
        shortlist=_shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.TIMEOUT
    assert calls == 1


def test_provider_classifies_wrapped_url_timeout_without_retrying() -> None:
    calls = 0

    def timeout_transport(url: str, body: bytes, timeout_seconds: float) -> bytes:
        nonlocal calls
        calls += 1
        raise URLError(TimeoutError())

    provider = OllamaProvider(
        model="qwen2.5-coder:7b",
        timeout_seconds=30,
        transport=timeout_transport,
    )
    result = provider.decide(
        action=RepairAction.FILL,
        original_test_id="search-input",
        shortlist=_shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.TIMEOUT
    assert calls == 1


def test_provider_classifies_transport_failure_without_retrying() -> None:
    calls = 0

    def failing_transport(url: str, body: bytes, timeout_seconds: float) -> bytes:
        nonlocal calls
        calls += 1
        raise OSError("connection refused")

    provider = OllamaProvider(
        model="qwen2.5-coder:7b",
        timeout_seconds=30,
        transport=failing_transport,
    )
    result = provider.decide(
        action=RepairAction.FILL,
        original_test_id="search-input",
        shortlist=_shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.CALL_FAILED
    assert calls == 1


@pytest.mark.parametrize(
    "response",
    [
        b"not-json",
        b"\xff",
        b'{"message":{"content":"x","content":"y"}}',
    ],
)
def test_provider_classifies_invalid_response_envelope_json(response: bytes) -> None:
    provider = OllamaProvider(
        model="qwen2.5-coder:7b",
        timeout_seconds=30,
        transport=CapturingTransport(response),
    )

    result = provider.decide(
        action=RepairAction.FILL,
        original_test_id="search-input",
        shortlist=_shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.INVALID_JSON


@pytest.mark.parametrize(
    "response",
    [
        b"[]",
        b"{}",
        b'{"message":null}',
        b'{"message":{"content":null}}',
    ],
)
def test_provider_classifies_invalid_response_envelope_schema(response: bytes) -> None:
    provider = OllamaProvider(
        model="qwen2.5-coder:7b",
        timeout_seconds=30,
        transport=CapturingTransport(response),
    )

    result = provider.decide(
        action=RepairAction.FILL,
        original_test_id="search-input",
        shortlist=_shortlist(),
    )

    assert result.outcome is OllamaDecisionOutcome.INVALID_SCHEMA


@pytest.mark.parametrize(
    "shortlist",
    [
        (_candidate("catalog-search-input"),),
        (
            _candidate("a-search-input"),
            _candidate("b-search-input"),
            _candidate("c-search-input"),
            _candidate("d-search-input"),
        ),
    ],
)
def test_provider_rejects_shortlist_outside_bounded_size_before_call(
    shortlist: tuple[LocatorCandidate, ...],
) -> None:
    transport = CapturingTransport(_response('{"decision":"abstain","candidate_test_id":null}'))
    provider = OllamaProvider(model="qwen2.5-coder:7b", timeout_seconds=30, transport=transport)

    with pytest.raises(ValueError, match="two or three"):
        provider.decide(
            action=RepairAction.FILL,
            original_test_id="search-input",
            shortlist=shortlist,
        )

    assert transport.calls == []


def test_provider_rejects_duplicate_candidate_ids_before_call() -> None:
    transport = CapturingTransport(_response('{"decision":"abstain","candidate_test_id":null}'))
    provider = OllamaProvider(model="qwen2.5-coder:7b", timeout_seconds=30, transport=transport)
    duplicate = (_candidate("catalog-search-input"), _candidate("catalog-search-input"))

    with pytest.raises(ValueError, match="unique"):
        provider.decide(
            action=RepairAction.FILL,
            original_test_id="search-input",
            shortlist=duplicate,
        )

    assert transport.calls == []


def test_provider_rejects_original_locator_in_shortlist_before_call() -> None:
    transport = CapturingTransport(_response('{"decision":"abstain","candidate_test_id":null}'))
    provider = OllamaProvider(model="qwen2.5-coder:7b", timeout_seconds=30, transport=transport)
    invalid = (_candidate("search-input"), _candidate("catalog-search-input"))

    with pytest.raises(ValueError, match="original failed locator"):
        provider.decide(
            action=RepairAction.FILL,
            original_test_id="search-input",
            shortlist=invalid,
        )

    assert transport.calls == []


def test_provider_rejects_action_incompatible_shortlist_before_call() -> None:
    transport = CapturingTransport(_response('{"decision":"abstain","candidate_test_id":null}'))
    provider = OllamaProvider(model="qwen2.5-coder:7b", timeout_seconds=30, transport=transport)
    invalid = (
        _candidate("catalog-search-input", editable=True),
        _candidate("header-search-input", editable=False),
    )

    with pytest.raises(ValueError, match="support the failed action"):
        provider.decide(
            action=RepairAction.FILL,
            original_test_id="search-input",
            shortlist=invalid,
        )

    assert transport.calls == []


def test_provider_configuration_rejects_blank_model_and_nonpositive_timeout() -> None:
    with pytest.raises(ValueError, match="model"):
        OllamaProvider(model="   ", timeout_seconds=30)

    with pytest.raises(ValueError, match="timeout_seconds"):
        OllamaProvider(model="qwen2.5-coder:7b", timeout_seconds=0)

    with pytest.raises(ValueError, match="timeout_seconds"):
        OllamaProvider(model="qwen2.5-coder:7b", timeout_seconds=float("inf"))
