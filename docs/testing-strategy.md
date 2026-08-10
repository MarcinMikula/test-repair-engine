# Testing strategy

## Purpose

TestRepairEngine is judged primarily by whether it restores broken automation
without weakening the original test.

Testing therefore verifies both internal decision logic and real runtime
behavior.

## Quality objective

The central product question is:

> Can TestRepairEngine recover the failed technical interaction and allow the
> unchanged original test to pass?

## Test levels

### Unit

Fast deterministic tests cover:

- strict contracts,
- ProjectProfile traceability shape,
- locator tokenization and scoring,
- action compatibility,
- ambiguity abstention,
- Playwright adapter orchestration with bounded fakes,
- runtime repair registration,
- final test-outcome correlation,
- RepairRecord persistence.

Unit tests start no browser and use no external model.

### E2E

Real Playwright execution is required for runtime-repair capability.

Sprint 1 contains two browser proofs against a controlled page:

```text
old search-input
new catalog-search-input
```

Baseline proof:

```text
repair not used
-> Playwright lookup/fill with search-input
-> timeout
```

Repair proof:

```text
current DOM contains catalog-search-input
-> deterministic candidate collection
-> fill compatibility filter
-> unique heuristic selection
-> retry succeeds
-> input contains original runtime value
-> RepairRecord runtime_result = recovered
-> finalized test_result = passed
```

The runtime value is used by the retry callback but is absent from persisted
repair evidence.

### Ecosystem acceptance

Repository-level E2E proof is necessary but not sufficient to close Sprint 1.

The final acceptance uses the current `qa-automation-framework` e-commerce POM
flow because the product boundary is intended to sit below concrete Page
Objects.

The acceptance sequence is:

```text
unchanged EcommerceSearchPage expects search-input
controlled demo target exposes catalog-search-input

TRE disabled
-> original framework test FAIL

TRE enabled
-> BasePage failure hook delegates to TRE
-> same fill action recovers
-> original framework test continues unchanged
-> existing assertions PASS
-> RepairRecord produced
```

The controlled target drift belongs to the acceptance setup, not a permanent
framework product change.

## STLC alignment

Each runtime repair slice follows:

```text
test analysis
-> define one failure and expected recovery

test planning
-> define scope, environment, evidence and exit criteria

test design
-> define fail-before, pass-after, ambiguity and failure cases

environment preparation
-> prepare controlled Playwright target

test execution
-> run baseline and repaired scenarios

exit evaluation
-> verify original test and RepairRecord

closure
-> keep only evidence needed for maintenance
```

## Sprint 1 exit criteria

Sprint 1 is complete only when all applicable checks pass:

- package installs in a clean virtual environment,
- Ruff lint passes,
- Ruff format check passes,
- Python compilation passes,
- all unit tests pass,
- real-browser baseline proves old test ID failure,
- real-browser repair proves deterministic recovery,
- ambiguous deterministic candidates cause abstention,
- only one retry is performed,
- no LLM is called,
- no runtime input value is persisted,
- `RepairRecord.runtime_result` is `recovered`,
- `RepairRecord.test_result` is `passed` only after the original test completes,
- current framework flow fails with controlled drift when TRE is disabled,
- the same unchanged framework test passes when TRE is enabled.

## CI

The quality matrix runs on Python 3.11 and 3.12:

- editable installation,
- Ruff lint,
- Ruff format check,
- compileall,
- unit tests.

A separate Python 3.12 browser job installs Chromium and runs the E2E repair
slice.

## Anti-cheating invariants

A passing test is not accepted as a valid repair if TestRepairEngine achieved it
by:

- deleting or changing assertions,
- changing expected results,
- skipping the failing scenario step,
- replacing required test data merely to obtain PASS,
- using unrestricted forced interaction,
- retrying indefinitely.

## Deferred validation

Sprint 1 does not attempt to prove:

- LLM fallback quality,
- general selector healing,
- timing/actionability repair,
- pytest-xdist/process-safe correlation,
- enterprise application coverage,
- automatic durable source updates.
