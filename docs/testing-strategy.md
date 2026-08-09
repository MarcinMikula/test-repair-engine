# Testing strategy

## Purpose

TestRepairEngine is judged primarily by whether it restores broken automation
without weakening the original test.

Testing therefore verifies both internal contracts and real runtime outcomes.

## Quality objective

The central product question is:

> Can TestRepairEngine recover the failed technical interaction and allow the
> unchanged original test to pass?

## Test levels

### Unit

Fast deterministic tests for:

- contracts,
- validation,
- candidate-scoring logic,
- parsers,
- persistence,
- bounded policies.

Unit tests use no browser or external model.

### Integration

Tests across component boundaries, for example:

```text
failure evidence
-> candidate finder
-> repair result
-> RepairRecord
```

or later:

```text
provider
-> structured response
-> candidate validation
```

### E2E

Real Playwright execution is required for every runtime-repair feature.

The expected pattern is:

```text
controlled broken application state
-> original test FAILS without repair
-> enable TestRepairEngine
-> repair occurs
-> original unchanged test PASSES
```

Mocks alone cannot close a runtime-repair feature.

## Sprint 0 verification

Sprint 0 verifies:

- package installation,
- strict contract validation,
- optional ecosystem traceability,
- successful `RepairRecord` JSON round trip,
- static code quality,
- Python compilation,
- CI execution on supported Python versions.

Sprint 0 intentionally does not claim repair capability.

## STLC alignment

Each runtime repair slice follows:

```text
test analysis
-> define one failure and expected recovery

test planning
-> define scope, environment, tools, and exit criteria

test design
-> define fail-before and pass-after scenarios

environment preparation
-> prepare controlled Playwright target

test execution
-> run baseline and repaired scenario

exit evaluation
-> verify original test and RepairRecord

closure
-> record only evidence needed for future maintenance
```

## Feature exit criteria

A runtime-repair feature is not complete until all applicable conditions hold:

- unit tests pass,
- integration tests pass where a component boundary exists,
- baseline failure is reproduced,
- runtime repair is observed,
- original test remains unchanged,
- original assertions execute,
- final test passes,
- `RepairRecord` reflects the actual repair,
- existing supported behavior does not regress.

## Anti-cheating invariants

A passing test is not accepted as a valid repair if TestRepairEngine achieved it
by:

- deleting or changing assertions,
- changing expected results,
- skipping the failing scenario step,
- replacing required test data merely to obtain PASS,
- using unrestricted forced interaction,
- retrying indefinitely.

## Current limitation

The project currently contains contracts and infrastructure only.

No runtime repair capability exists in Sprint 0.
