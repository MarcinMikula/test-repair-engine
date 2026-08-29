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
normal Playwright interaction
        |
        +-- success -> original test continues
        |
        `-- failure
              |
              v
       framework eligibility classifier
              |
              +-- TimeoutError + original count == 0 --------+
              +-- qualified strict mode + count > 1 ---------+
              +-- original count == 1 -> original failure    |
              `-- generic/unconfirmed -> original failure    |
                                                           v
                                                  TestRepairEngine
                                                           |
                                            exact original-count probe
                                                           |
                 +------------------+-----------------------+----------------+
                 |                  |                                        |
            count == 1         probe failure                           count 0 or >1
            fail closed         fail closed                                  |
                                                                             v
                                                           bounded candidate collection
                                                                             |
                                                           action compatibility + ranking
                                                                             |
                       +-------------------+-------------------+---------------+
                       |                   |                   |
                  unique winner      bounded ambiguity      weak / broad
                       |                   |                   |
                       |             optional one-call       fail closed
                       |             Ollama proposal
                       |             + local validation
                       +-------------------+
                                 |
                                 v
                          one browser retry
                                 |
                                 v
                       unchanged test continues
                                 |
                                 v
                     original assertions execute
                                 |
                                 v
                    pytest finalizes RepairRecord
```

The complete original test result remains authoritative. Framework eligibility
and TRE substitution authority are separate safety boundaries.

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

Normal Playwright execution always runs first. The reusable mechanical helper
then decides whether the observed failure is eligible for locator repair.

```text
TimeoutError + original test-id count == 0
-> optional TRE locator-drift handoff

TimeoutError + original test-id count == 1
-> locator still resolves uniquely
-> preserve original failure

qualified strict-mode violation + original test-id count > 1
-> optional TRE handoff

generic non-timeout Playwright error
-> no TRE handoff

failed count confirmation
-> fail closed
```

The framework owns this classifier because it owns normal Playwright execution.
Runtime repair remains outside the successful-path dependency chain.

## Sprint 1 deterministic candidate model

Sprint 1 handles `LocatorKind.TEST_ID` only.

Candidate collection persists no raw page payload. `LocatorKind.TEST_ID` is a
logical locator kind. `data-testid` is the default physical attribute, while the
adapter may receive another explicitly configured Playwright test-id attribute
such as `data-test`.

For each bounded candidate, the adapter uses only structural runtime facts needed
for selection:

- the value of the active physical test-id attribute,
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

## Original-target safety invariant

Before candidate collection can authorize substitution, TRE performs an exact
browser-side count of elements whose active physical test-id attribute equals
the original logical test ID.

```text
exact original count == 1
-> no substitution
-> fail closed

exact probe raises PlaywrightError
-> fail closed

exact original count == 0
-> locator-drift recovery may continue

exact original count > 1
-> separately qualified strict-mode recovery may continue
```

This exact probe is independent of the bounded candidate collector. Candidate
performance limits must not hide a unique original element from a safety
decision.

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

1. create one process-local run ID for each pytest process/session,
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

Under `pytest-xdist`, each worker process initializes its own process-local TRE
runtime state and run ID. S5.1 directly qualified two explicit worker processes
writing independent RepairRecords into one shared output directory while
preserving separate final pytest outcomes. That evidence is bounded to the tested
two-worker scenario and does not establish unrestricted concurrency guarantees.

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

## Current validated boundary

Implemented and validated in TRE / its supported framework seam:

- strict locator-repair contracts,
- deterministic logical `TEST_ID` ranking,
- default `data-testid` plus explicit custom test-id attribute support,
- bounded candidate collection,
- exact unbounded original-count protection before substitution,
- explicit bounded-ambiguity classification,
- optional one-call Ollama only for 2-3 candidate ambiguity,
- strict provider-response and local allowlist validation,
- one-retry recovery,
- auditable RepairRecord v0.2 evidence,
- pytest final-result correlation and collision-safe persistence,
- bounded two-worker pytest-xdist qualification,
- zero-match timeout locator-drift framework eligibility,
- qualified strict-mode multiple-match framework eligibility,
- framework rejection of unique-match actionability timeouts,
- TRE defense-in-depth rejection of substitution when the original still
  resolves exactly once,
- controlled, frozen real-app, live external and merged-main validation.

Still outside the current boundary:

- non-test-id locator families,
- generic timing/actionability healing,
- source-code patching,
- TestCartographer compatibility interpretation,
- API/SOM repair,
- broad pytest-xdist/concurrency guarantees beyond S5.1,
- general LLM robustness across independently evolved dynamic frontends,
- automatic human-review execution workflow.
