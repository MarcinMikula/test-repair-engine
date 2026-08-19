# Architecture

## Purpose

TestRepairEngine performs bounded runtime recovery of technical failures in
Playwright tests.

It is not a test framework, application model, test generator, source-code
rewriter, or general maintenance platform.

## Core lifecycle

```text
pytest / Playwright test
        |
        v
technical interaction fails
        |
        v
framework interaction hook
        |
        v
TestRepairEngine
        |
        +-- collect bounded structural candidates
        +-- filter by action compatibility
        +-- rank deterministically
        |
        +-- unique winner --------------------+
        |                                     |
        +-- bounded ambiguity                  |
        |      |                               |
        |      +-- LLM disabled -> fail closed |
        |      |                               |
        |      `-- one Ollama proposal         |
        |             -> local validation      |
        |             -> validated selection -+
        |
        `-- weak / too broad -> fail closed
                                              |
                                              v
                                    one browser retry
                                              |
                                              v
                                    original test continues
                                              |
                                              v
                                    original assertions execute
                                              |
                                              v
                                    pytest finalizes RepairRecord
```

The complete original test result remains authoritative.

## Ecosystem ownership

```text
qa-automation-framework
-> execution

TestRepairEngine
-> runtime recovery

TestCartographer
-> application knowledge, durable maintenance, evolution
```

These responsibilities remain separate.

## Framework integration boundary

Concrete Page Objects must not know that TestRepairEngine exists.

The intended integration point is the small reusable mechanical interaction
layer:

```text
Concrete Page Object
        |
        v
BasePage / reusable interaction helper
        |
        v
normal Playwright interaction
        |
        +-- success -> continue normally
        |
        `-- timeout -> optional TestRepairEngine hook
                         |
                         +-- disabled/unavailable -> re-raise original failure
                         `-- recovered -> continue original test
```

The normal Playwright operation always runs first. Runtime repair is therefore
not on the successful-path dependency chain.

## Sprint 1 deterministic candidate model

Sprint 1 handles `LocatorKind.TEST_ID` only.

Candidate collection persists no raw page payload. For each bounded candidate,
the adapter uses only structural runtime facts needed for selection:

- `data-testid`,
- tag name,
- explicit ARIA role when present,
- visibility,
- enabled state,
- editable state.

It does not collect:

- input values,
- arbitrary text,
- HTML,
- screenshots,
- credentials,
- network bodies.

## Action compatibility

Candidate scoring begins only after structural filtering.

For `fill`, a candidate must be visible, enabled, and editable or use a normal
fillable tag such as `input` or `textarea`.

For `click`, the first slice accepts normal clickable tags or explicit clickable
roles.

This prevents a textually similar but mechanically incompatible element from
winning solely because its test ID looks familiar.

## Deterministic ranking

Candidate similarity combines:

- normalized token overlap,
- string sequence similarity,
- a small bonus when the old locator tokens are preserved inside a more specific
  new test ID.

Selection requires both:

- a minimum score,
- a minimum lead over the second candidate.

The engine abstains when the evidence is too weak or the ambiguity is too broad.
A 2–3 candidate ambiguity is a distinct machine-readable state that may become
eligible for the optional Sprint 2 Ollama fallback.

## Sprint 2 bounded Ollama boundary

The local model is available only after deterministic selection returns
`AMBIGUOUS`. `NO_CANDIDATES`, `BELOW_THRESHOLD`, `AMBIGUOUS_TOO_BROAD` and a
deterministic `SELECTED` result do not grant model authority.

The provider receives a shortlist of 2–3 action-compatible candidates without
their deterministic scores. It may return one supplied candidate or abstain.

The runtime then validates the response again against the exact shortlist before
execution:

```text
deterministic AMBIGUOUS
-> at most one Ollama call
-> strict response parsing
-> exact local allowlist validation
-> at most one browser retry
```

Provider transport failure, timeout, invalid JSON, invalid schema, abstention or
an outside-allowlist selection authorizes no retry.

`candidate_count` in `RepairRecord` is the number of all ranked
action-compatible candidates considered by deterministic selection. It is not
the shortlist length. The bounded shortlist is a separate subset used only for
eligible ambiguity.

Once a real LLM call occurs, `selected_score` is not recorded as though a
deterministic score explained the model's decision.

## Retry boundary

The current runtime performs at most one retry of the failed interaction with an
authorized replacement test ID, regardless of whether the replacement came from
the deterministic layer or a validated LLM proposal.

It does not:

- loop until something passes,
- use `force=True` as a generic workaround,
- modify assertions,
- modify expected outcomes,
- modify test data,
- patch source code during execution.

If the replacement also fails, control returns to the original Playwright
failure path.

## pytest correlation

The package registers a pytest plugin, but repair remains opt-in through:

```text
--test-repair-engine
```

The plugin owns only runtime correlation:

1. create one run ID for the pytest session,
2. associate repairs with the current pytest node ID,
3. remember whether any pytest phase failed,
4. finalize pending repair records after teardown,
5. persist `test_result=passed` or `failed`.

This preserves the distinction between:

```text
ACTION_RECOVERED
!=
TEST_VALIDATED
```

A recovered interaction followed by a failed assertion remains a failed test.

## TestCartographer boundary

TestRepairEngine does not import TestCartographer.

Optional project identity is carried as:

```text
project_profile_id
project_profile_revision
configuration_fingerprint
```

TestCartographer remains responsible for deciding whether the project context is
still compatible and whether durable maintenance requires re-observation,
repository resnapshot, review, or a source update.

## Current Sprint 2 boundary

Implemented in TestRepairEngine:

- strict locator-repair contracts,
- deterministic `data-testid` ranking,
- bounded Playwright candidate collection,
- explicit bounded-ambiguity classification,
- optional one-call Ollama proposal only for 2–3 candidate ambiguity,
- strict local provider-response and execution-allowlist validation,
- one-retry recovery,
- auditable LLM runtime evidence in RepairRecord v0.2,
- runtime RepairRecord registration,
- pytest final-result correlation,
- collision-safe JSON persistence,
- unit and controlled real-browser tests,
- unchanged `qa-automation-framework` acceptance.

Still outside the current boundary:

- non-test-id locator families,
- timing/actionability repair taxonomy,
- source-code patching,
- TestCartographer compatibility interpretation,
- API/SOM repair,
- concurrent pytest/xdist guarantees,
- general LLM robustness across independently evolved dynamic frontends.
