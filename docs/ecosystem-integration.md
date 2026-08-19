# Ecosystem integration

## Purpose

TestRepairEngine participates in the same automation lifecycle as
`qa-automation-framework` and TestCartographer without merging their ownership
boundaries.

## Boundary 1 — framework to TestRepairEngine

The framework owns normal test execution.

A generic mechanical interaction helper may call TestRepairEngine only after a
repairable Playwright interaction fails.

The current relevant handoff is equivalent to:

```text
action
locator kind = test_id
original test ID
Page Object class when available
mechanical helper method when available
optional project/context traceability
```

The runtime callback used to retry a fill may close over the input value, but the
value is not inspected or persisted by TestRepairEngine.

If TestRepairEngine is not installed, not enabled, cannot find a safe candidate,
or cannot recover the retry, the original Playwright failure remains
controlling.

## Boundary 2 — runtime recovery

The current runtime still repairs one narrow `data-testid` drift interaction at
a time, but Sprint 2 adds one bounded ambiguity escalation path.

```text
old data-testid
-> bounded current candidates
-> structural action filter
-> deterministic ranking

unique candidate
-> retry same interaction once

2–3 candidate ambiguity + LLM enabled
-> one local Ollama proposal
-> exact deterministic validation
-> retry same interaction once only when validated

weak / too broad / invalid model result
-> no retry
-> original Playwright failure remains controlling
```

A recovered interaction allows the same test invocation to continue.
TestRepairEngine does not own business correctness. The LLM also does not own
execution authority; the deterministic runtime boundary does.

## Boundary 3 — pytest outcome

A successful retry creates runtime evidence but does not yet prove the test.

The pytest plugin finalizes the repair after test teardown:

```text
runtime_result = recovered
+
unchanged original pytest test = passed

=> test_result = passed
```

If any pytest phase fails, the repair record is finalized with
`test_result=failed`.

## Boundary 4 — TestRepairEngine to TestCartographer

A finalized repair may carry an optional `ProjectReference` with exactly:

```text
project_profile_id
project_profile_revision
configuration_fingerprint
```

The names align with the current TestCartographer ProjectProfile reference
boundary. TestRepairEngine still treats them as opaque values.

TestRepairEngine must not:

- import TestCartographer,
- determine ProjectProfile compatibility,
- invalidate application knowledge,
- interpret workspace drift,
- decide whether runtime repair should become a permanent source change.

Those decisions belong to TestCartographer.

## Current TestCartographer compatibility model

TestCartographer currently owns selective compatibility such as:

```text
environment/base URL change -> REOBSERVE
workspace binding change    -> RESNAPSHOT
guided-intake binding drift -> REVIEW_REQUIRED
```

A successful runtime repair does not override those rules.

For example, a repair performed under ProjectProfile revision 2 may later be
reviewed under revision 3. TestRepairEngine records the identity used during the
repair; TestCartographer decides whether the evidence is still suitable for
durable maintenance.

## Context traceability

`CartographerTraceability` may additionally carry:

```text
context_id
process_id
element_id
```

All values remain optional so TestRepairEngine can operate:

- inside the full ecosystem,
- with partial traceability,
- completely independently of TestCartographer.

## ExecutionEvidenceBundle and RepairRecord are different

The existing framework-side TestCartographer evidence contract answers what the
test execution did and where it stopped.

`RepairRecord` answers what TestRepairEngine changed temporarily during that
execution.

A runtime repair can turn the final pytest result green, so the repair action
must not be inferred from a normal passing execution record.

The two artefacts are complementary:

```text
ExecutionEvidenceBundle
-> execution facts

RepairRecord
-> runtime recovery facts

TestCartographer
-> durable maintenance interpretation
```

## Supported framework acceptance

Sprint 2 acceptance exercised the actual `qa-automation-framework` integration
boundary rather than a TestRepairEngine-only harness.

The same existing e-commerce checkout test and its original assertions were run
in three configurations:

```text
TRE disabled
-> broken search-input remains a normal Playwright failure

TRE enabled, LLM disabled
-> deterministic bounded ambiguity
-> no model call
-> fail closed

TRE enabled, real Ollama enabled
-> validated catalog-search-input selection
-> one retry
-> unchanged framework test passes
```

The authoritative S2.8 evidence run is `run-20260819T171427Z`. The acceptance
did not modify TestRepairEngine source, framework source, the target test or its
assertions to obtain PASS.

This validates the supported integration for the current bounded capability. It
does not transfer durable-maintenance authority from TestCartographer to
TestRepairEngine.

## Durable maintenance

```text
TestRepairEngine
-> proves one runtime candidate can recover the interaction

TestCartographer
-> evaluates current context and decides durable maintenance

qa-automation-framework
-> receives accepted long-lived automation changes
```

TestRepairEngine does not write framework source automatically.
