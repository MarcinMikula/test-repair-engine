# Architecture

## Purpose

TestRepairEngine performs bounded runtime recovery of technical failures in
Playwright tests.

It is not a test framework, application model, test generator, or general
maintenance platform.

## Core lifecycle

```text
pytest / Playwright test
        |
        v
technical interaction fails
        |
        v
TestRepairEngine
        |
        +-- collect minimal runtime evidence
        +-- find repair candidate
        +-- validate candidate
        +-- retry failed interaction
                |
                v
        original test continues
                |
                v
        original assertions execute
```

The complete test result remains authoritative.

## Ecosystem ownership

```text
qa-automation-framework
-> execution

TestRepairEngine
-> runtime recovery

TestCartographer
-> application knowledge, durable maintenance, evolution
```

These responsibilities must remain separate.

## Framework integration

Concrete Page Objects must not know that TestRepairEngine exists.

Target integration:

```text
Concrete Page Object
        |
        v
BasePage / reusable interaction layer
        |
        v
Playwright interaction
        |
        v
failure hook
        |
        v
TestRepairEngine
```

With TestRepairEngine disabled or absent, framework behavior must remain normal
Playwright behavior.

## Repair boundary

The first version may repair technical interaction mechanics such as locator
drift.

It must not modify:

- assertions,
- expected business outcomes,
- scenario meaning,
- test-data expectations,
- application rules.

## Runtime success vs test success

Two different states are tracked.

### Runtime recovery

The failed Playwright interaction was successfully retried.

### Test validation

The complete unchanged original test subsequently passed.

A runtime recovery does not imply test success.

## Recovery order

The intended v0.1 repair ladder is:

```text
failure
-> deterministic/heuristic candidate search
-> candidate validation
-> retry

if unresolved:
-> bounded LLM fallback
-> candidate validation
-> retry

if unresolved:
-> escalation
```

The project does not call an LLM when a cheaper deterministic mechanism already
solves the problem.

## Current Sprint 0 boundary

Implemented:

- core contracts,
- RepairRecord persistence,
- tests,
- CI.

Not implemented:

- failure interception,
- browser context collection,
- candidate ranking,
- Playwright retry,
- LLM fallback,
- pytest final-result correlation,
- source patching.
