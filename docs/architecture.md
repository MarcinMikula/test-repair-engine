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
        +-- abstain if weak or ambiguous
        +-- retry one selected replacement
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

The engine abstains when the evidence is too weak or ambiguous.

## Retry boundary

Sprint 1 performs one retry of the failed interaction with the selected
replacement test ID.

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

## Current Sprint 1 boundary

Implemented in TestRepairEngine:

- strict locator-repair contracts,
- deterministic `data-testid` ranking,
- bounded Playwright candidate collection,
- one-retry recovery,
- runtime RepairRecord registration,
- pytest final-result correlation,
- JSON persistence,
- unit and real-browser tests.

Still outside Sprint 1:

- Ollama or other LLM fallback,
- non-test-id locator families,
- timing/actionability repair taxonomy,
- source-code patching,
- TestCartographer compatibility interpretation,
- API/SOM repair,
- concurrent pytest/xdist guarantees.
