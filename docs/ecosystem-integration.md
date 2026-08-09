# Ecosystem integration

## Purpose

TestRepairEngine participates in the same automation lifecycle as
`qa-automation-framework` and TestCartographer without tightly coupling their
runtime implementations.

## Boundary 1 — framework to TestRepairEngine

The framework owns normal test execution.

A future generic interaction hook may provide TestRepairEngine with a
`RepairRequest` after a Playwright interaction fails.

The request contains structural repair information only.

Examples:

- action kind,
- original locator,
- pytest node ID,
- Page Object name,
- method name,
- optional ecosystem traceability.

Test input values, credentials, arbitrary page content, and business assertions
do not belong in the persisted contract.

## Boundary 2 — TestRepairEngine runtime recovery

TestRepairEngine attempts to restore the failed interaction.

The first supported repair class will be locator drift.

A successful repair allows the same test invocation to continue.

TestRepairEngine does not own business correctness. The existing test assertions
remain unchanged.

## Boundary 3 — TestRepairEngine to TestCartographer

Each attempt may produce a versioned `RepairRecord`.

A record may contain an optional `ProjectReference`:

```text
profile_id
revision
configuration_fingerprint
```

These values are opaque to TestRepairEngine.

TestRepairEngine must not:

- import TestCartographer,
- determine ProjectProfile compatibility,
- invalidate application knowledge,
- interpret workspace drift,
- decide whether a repair should become permanent.

Those decisions belong to TestCartographer.

## ProjectProfile relationship

When the wider ecosystem supplies current TestCartographer project identity,
TestRepairEngine records it with the repair.

Example:

```text
runtime repair
performed under ProjectProfile revision 2
        |
        v
later TestCartographer maintenance
        |
        v
current ProjectProfile revision 3
        |
        v
TestCartographer decides whether re-observation or review is required
```

TestRepairEngine only carries the evidence.

## Context traceability

`CartographerTraceability` may additionally carry:

```text
context_id
process_id
element_id
```

All values are optional.

This allows TestRepairEngine to work:

- inside the complete ecosystem,
- with only partial traceability,
- completely independently of TestCartographer.

## Durable maintenance

A runtime recovery and a durable framework change are different operations.

```text
TestRepairEngine
-> proves a runtime candidate can recover the interaction

TestCartographer
-> decides whether accepted project/context knowledge should change

qa-automation-framework
-> contains the resulting accepted automation code
```

This prevents TestRepairEngine from becoming a second application-model or
repository-maintenance system.
