"""Strict Ollama contract for bounded locator-ambiguity decisions.

The provider owns only one structured decision call. It has no browser execution
authority; runtime code decides whether an exact validated shortlist selection
may be retried.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from test_repair_engine.candidate_finder import LocatorCandidate, candidate_supports_action
from test_repair_engine.contracts import RepairAction

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_TEMPERATURE = 0
_DEFAULT_SEED = 42
_MIN_SHORTLIST_SIZE = 2
_MAX_SHORTLIST_SIZE = 3

_SYSTEM_PROMPT = """You resolve one bounded locator ambiguity for TestRepairEngine.
You may select only a candidate_test_id supplied in the request.
Do not invent, rewrite, normalize, or repair a locator.
If the supplied metadata is insufficient to choose safely, abstain.
Return only JSON matching the supplied response schema.
"""

Transport = Callable[[str, bytes, float], bytes]


class OllamaDecisionOutcome(StrEnum):
    """Classified outcome of one isolated Ollama ambiguity decision."""

    CALL_FAILED = "call_failed"
    TIMEOUT = "timeout"
    INVALID_JSON = "invalid_json"
    INVALID_SCHEMA = "invalid_schema"
    ABSTAINED = "abstained"
    OUTSIDE_ALLOWLIST = "outside_allowlist"
    VALIDATED_SELECTION = "validated_selection"


@dataclass(frozen=True, slots=True)
class OllamaDecisionResult:
    """Validated provider result without browser or repair execution authority."""

    outcome: OllamaDecisionOutcome
    selected_test_id: str | None = None
    reason: str | None = None


class _DuplicateJsonKeyError(ValueError):
    pass


class _InvalidResponseJson(ValueError):
    pass


class _InvalidResponseSchema(ValueError):
    pass


def build_decision_schema(shortlist: tuple[LocatorCandidate, ...]) -> dict[str, Any]:
    """Build the exact provider-facing schema for one bounded shortlist."""

    allowed_ids = sorted(candidate.test_id for candidate in shortlist)
    return {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["select"]},
                    "candidate_test_id": {"type": "string", "enum": allowed_ids},
                },
                "required": ["decision", "candidate_test_id"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["abstain"]},
                    "candidate_test_id": {"type": "null"},
                },
                "required": ["decision", "candidate_test_id"],
                "additionalProperties": False,
            },
        ]
    }


def build_decision_payload(
    *,
    model: str,
    action: RepairAction,
    original_test_id: str,
    shortlist: tuple[LocatorCandidate, ...],
    page_object: str | None = None,
    method_name: str | None = None,
) -> dict[str, Any]:
    """Build one non-streaming structured-output request for Ollama chat."""

    _validate_shortlist(action, original_test_id, shortlist)
    schema = build_decision_schema(shortlist)
    provider_candidates = sorted(shortlist, key=lambda candidate: candidate.test_id)
    context = {
        "action": action.value,
        "original_test_id": original_test_id,
        "page_object": page_object,
        "method_name": method_name,
        "candidates": [
            {
                "test_id": candidate.test_id,
                "tag_name": candidate.tag_name,
                "role": candidate.role,
                "visible": candidate.visible,
                "enabled": candidate.enabled,
                "editable": candidate.editable,
            }
            for candidate in provider_candidates
        ],
        "response_schema": schema,
    }
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, sort_keys=True)},
        ],
        "stream": False,
        "format": schema,
        "options": {
            "temperature": _DEFAULT_TEMPERATURE,
            "seed": _DEFAULT_SEED,
        },
    }


def parse_model_decision(
    content: str,
    shortlist: tuple[LocatorCandidate, ...],
) -> OllamaDecisionResult:
    """Parse and deterministically validate model content against the shortlist."""

    try:
        parsed = _loads_without_duplicate_keys(content)
    except (json.JSONDecodeError, _DuplicateJsonKeyError):
        return OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.INVALID_JSON,
            reason="Model response is not unambiguous JSON.",
        )

    if not isinstance(parsed, dict) or set(parsed) != {"decision", "candidate_test_id"}:
        return OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.INVALID_SCHEMA,
            reason="Model response does not match the two-field decision contract.",
        )

    decision = parsed["decision"]
    candidate_test_id = parsed["candidate_test_id"]

    if decision == "abstain":
        if candidate_test_id is not None:
            return OllamaDecisionResult(
                outcome=OllamaDecisionOutcome.INVALID_SCHEMA,
                reason="Abstention requires candidate_test_id to be null.",
            )
        return OllamaDecisionResult(outcome=OllamaDecisionOutcome.ABSTAINED)

    if decision != "select" or not isinstance(candidate_test_id, str):
        return OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.INVALID_SCHEMA,
            reason="Selection requires decision='select' and a string candidate_test_id.",
        )

    allowed_ids = {candidate.test_id for candidate in shortlist}
    if candidate_test_id not in allowed_ids:
        return OllamaDecisionResult(
            outcome=OllamaDecisionOutcome.OUTSIDE_ALLOWLIST,
            reason="Model selected a candidate outside the supplied shortlist.",
        )

    return OllamaDecisionResult(
        outcome=OllamaDecisionOutcome.VALIDATED_SELECTION,
        selected_test_id=candidate_test_id,
    )


class OllamaProvider:
    """One-call Ollama client for an already-bounded locator ambiguity."""

    def __init__(
        self,
        *,
        model: str,
        timeout_seconds: float,
        transport: Transport | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be blank.")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive.")

        self._model = model.strip()
        self._timeout_seconds = timeout_seconds
        self._transport = transport or _post_json

    def decide(
        self,
        *,
        action: RepairAction,
        original_test_id: str,
        shortlist: tuple[LocatorCandidate, ...],
        page_object: str | None = None,
        method_name: str | None = None,
    ) -> OllamaDecisionResult:
        """Make exactly one provider call, then validate the returned selection."""

        payload = build_decision_payload(
            model=self._model,
            action=action,
            original_test_id=original_test_id,
            shortlist=shortlist,
            page_object=page_object,
            method_name=method_name,
        )
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        url = f"{_DEFAULT_BASE_URL}/api/chat"

        try:
            raw_response = self._transport(url, body, self._timeout_seconds)
        except TimeoutError:
            return OllamaDecisionResult(
                outcome=OllamaDecisionOutcome.TIMEOUT,
                reason="Ollama request timed out.",
            )
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                return OllamaDecisionResult(
                    outcome=OllamaDecisionOutcome.TIMEOUT,
                    reason="Ollama request timed out.",
                )
            return OllamaDecisionResult(
                outcome=OllamaDecisionOutcome.CALL_FAILED,
                reason="Ollama request failed before a usable response was received.",
            )
        except OSError:
            return OllamaDecisionResult(
                outcome=OllamaDecisionOutcome.CALL_FAILED,
                reason="Ollama request failed before a usable response was received.",
            )

        try:
            content = _extract_message_content(raw_response)
        except _InvalidResponseJson:
            return OllamaDecisionResult(
                outcome=OllamaDecisionOutcome.INVALID_JSON,
                reason="Ollama response envelope is not unambiguous JSON.",
            )
        except _InvalidResponseSchema:
            return OllamaDecisionResult(
                outcome=OllamaDecisionOutcome.INVALID_SCHEMA,
                reason=(
                    "Ollama response envelope does not contain string assistant message content."
                ),
            )

        return parse_model_decision(content, shortlist)


def _validate_shortlist(
    action: RepairAction,
    original_test_id: str,
    shortlist: tuple[LocatorCandidate, ...],
) -> None:
    if not original_test_id:
        raise ValueError("original_test_id must not be empty.")
    if not _MIN_SHORTLIST_SIZE <= len(shortlist) <= _MAX_SHORTLIST_SIZE:
        raise ValueError("shortlist must contain exactly two or three candidates.")

    test_ids = [candidate.test_id for candidate in shortlist]
    if any(not test_id for test_id in test_ids):
        raise ValueError("shortlist candidate test_id must not be empty.")
    if len(set(test_ids)) != len(test_ids):
        raise ValueError("shortlist candidate test_id values must be unique.")
    if original_test_id in test_ids:
        raise ValueError("shortlist must not contain the original failed locator.")
    if any(not candidate_supports_action(candidate, action) for candidate in shortlist):
        raise ValueError("every shortlist candidate must support the failed action.")


def _loads_without_duplicate_keys(value: str) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for key, item in pairs:
            if key in parsed:
                raise _DuplicateJsonKeyError(key)
            parsed[key] = item
        return parsed

    return json.loads(value, object_pairs_hook=reject_duplicate_keys)


def _extract_message_content(raw_response: bytes) -> str:
    try:
        decoded = raw_response.decode("utf-8")
        envelope = _loads_without_duplicate_keys(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKeyError) as exc:
        raise _InvalidResponseJson from exc

    if not isinstance(envelope, dict):
        raise _InvalidResponseSchema
    message = envelope.get("message")
    if not isinstance(message, dict):
        raise _InvalidResponseSchema
    content = message.get("content")
    if not isinstance(content, str):
        raise _InvalidResponseSchema
    return content


def _post_json(url: str, body: bytes, timeout_seconds: float) -> bytes:
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # S310 is suppressed because the provider always supplies the fixed local Ollama URL.
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        return response.read()
