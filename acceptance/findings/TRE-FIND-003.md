# TRE-FIND-003 - strict-mode multiple-match failures do not reach TestRepairEngine through the framework handoff

## Status

**OPEN - evidence-qualified integration-boundary capability gap; correction not yet implemented.**

## Discovery context

Validation slices:

~~~text
S6.1 - strict-mode / multiple-match qualification
S6.2 - strict-mode core isolation
~~~

Authoritative pre-fix evidence:

~~~text
S6.1:
run-20260826T160742Z

S6.2:
run-20260826T161227Z
~~~

Frozen TestRepairEngine revision:

~~~text
d1b5860849b7aa3d93846fa22834a31d278b8ad1
~~~

Frozen `qa-automation-framework` revision exercised by S6.1:

~~~text
4d916dea8190bc59ef8c9dd5aa78aa31dbbf16a6
~~~

Both qualification slices kept TestRepairEngine source frozen. S6.1 also kept
the framework source frozen. LLM fallback remained disabled.

Large runtime artifacts remain outside the repository under:

~~~text
TestRepairEngine-local-artifacts/
`-- acceptance/
    |-- s6.1-strict-mode-qualification/
    |   `-- run-20260826T160742Z/
    `-- s6.2-strict-mode-core-isolation/
        `-- run-20260826T161227Z/
~~~

## S6.1 - framework handoff observation

The controlled page exposed two visible buttons with the same original locator:

~~~text
data-testid="save-action"
count = 2
~~~

The normal unchanged framework interaction:

~~~text
BasePage.click_by_test_id("save-action")
~~~

raised a real Playwright strict-mode violation.

Observed facts:

~~~text
exception captured             = true
Playwright Error               = true
Playwright TimeoutError        = false
strict-mode violation text     = true
matching locator count         = 2
framework repair hook calls    = 0
strict-case RepairRecords      = 0
~~~

The same qualification run contained a positive timeout control:

~~~text
old locator:
save-action

current locator:
catalog-save-action
~~~

That control proved the existing integration was active:

~~~text
repair hook calls              = 1
replacement                    = catalog-save-action
runtime_result                 = recovered
test_result                    = passed
LLM called                     = false
~~~

Therefore the strict-mode case did not miss TestRepairEngine because the plugin,
runtime or harness was disabled. It missed TestRepairEngine because the current
framework handoff delegates the tested test-id helper only after
`PlaywrightTimeoutError`.

## S6.2 - current TestRepairEngine core isolation

S6.2 bypassed the framework exception gate and handed the already observed
strict-mode failure explicitly to the unchanged TestRepairEngine core.

### Case A - duplicates only

DOM:

~~~text
save-action
save-action
~~~

The production collector saw both structural candidates, but the deterministic
ranker intentionally excludes candidates whose test ID is identical to the
original locator.

Observed result:

~~~text
collector candidate count      = 2
ranked candidate_count         = 0
runtime_result                 = failed
test_result                    = failed
retry calls                    = 0
LLM called                     = false
~~~

The original strict-mode failure remained the final test oracle.

This is the desired safe behavior. Duplicate identity alone does not authorize
TRE to choose one matching element or to bypass Playwright strictness.

### Case B - duplicates plus one distinct replacement

DOM:

~~~text
save-action
save-action
primary-save-action
~~~

After explicit handoff to the unchanged production core:

~~~text
save-action
-> primary-save-action
-> heuristic
-> score 0.786667
-> runtime_result recovered
-> test_result passed
-> LLM called false
~~~

The retry clicked the distinct replacement successfully.

This proves that the existing deterministic TRE core already has a bounded
recovery path for a strict-mode interaction when runtime evidence contains a
separate safe replacement candidate.

## Classification

This finding is an **evidence-qualified integration-boundary capability gap**.

It is not evidence that every Playwright strict-mode violation should be healed.

The observed boundary is narrower:

~~~text
repairable test-id strict-mode failure
+
distinct safe replacement candidate exists
+
current TRE core could recover after explicit handoff
+
current framework handoff does not invoke TRE for that failure type
~~~

The current framework also deliberately protects generic non-timeout
`PlaywrightError` from repair delegation. That safety boundary must not be removed
by changing the helper to catch every Playwright error indiscriminately.

## Ownership

The missing handoff is owned by the reusable mechanical interaction seam in
`qa-automation-framework`.

Current evidence does **not** justify a TestRepairEngine product-source change.

TestRepairEngine owns the bounded repair decision after the framework delegates a
repairable failed interaction. The framework owns normal Playwright execution and
classification of whether a failed interaction should enter the optional TRE
handoff.

The finding remains in the TestRepairEngine acceptance chain because TRE
validation exposed the missing path and the post-fix acceptance must prove that
the supported ecosystem interaction can reach TRE correctly.

## Expected behavior

For framework test-id click/fill helpers:

1. normal Playwright interaction still runs first;
2. the existing timeout recovery path remains unchanged;
3. a specifically qualified strict-mode multiple-match failure may enter the
   same bounded TRE handoff;
4. generic non-timeout Playwright errors must continue to bypass TRE;
5. if TRE cannot authorize a replacement, the original strict-mode failure
   remains controlling;
6. duplicate original test IDs alone must not authorize arbitrary
   `.first()`, `.last()`, `.nth()`, forced interaction or equivalent selection;
7. a successful runtime repair still does not imply final test success.

The exact narrow classifier belongs to the correction design and must be proven by
fail-before coverage before implementation.

## Scope of correction

In scope:

- `qa-automation-framework` BasePage test-id interaction handoff,
- narrow recognition of the qualified strict-mode multiple-match case,
- existing timeout behavior preserved,
- generic non-timeout Playwright-error protection preserved,
- one existing TRE handoff and one existing retry budget,
- fail-closed behavior when TRE returns no replacement,
- real-browser post-fix validation through the framework seam.

Out of scope:

- catching all `PlaywrightError`,
- choosing among duplicate original test IDs,
- `.first()`, `.last()` or `.nth()` as generic repair,
- `force=True`,
- new locator families,
- TestRepairEngine scoring or threshold changes,
- broader ambiguity or LLM authority,
- extra browser retries,
- RepairRecord schema changes,
- source rewriting,
- TestCartographer durable-maintenance behavior.

## Acceptance basis

The finding may close only after separate correction evidence proves:

1. a committed fail-before test on the framework seam reproduces the missing
   strict-mode delegation;
2. the smallest framework correction makes the qualified strict-mode case enter
   the existing TRE handoff;
3. the existing generic non-timeout Playwright-error protection remains green;
4. the existing timeout handoff remains green;
5. duplicate-only strict-mode evidence still fails closed;
6. a distinct safe replacement can recover through the real framework path;
7. if TRE declines recovery, the original strict-mode Playwright failure is
   re-raised;
8. no TestRepairEngine product-source change is required unless new evidence
   contradicts S6.2;
9. a new immutable post-fix browser run validates the unchanged interaction
   oracle;
10. LLM escalation remains unearned unless deterministic evidence is genuinely
    ambiguous.

## Current closure state

**OPEN.**

No correction commit or post-fix acceptance run exists yet.

No GitHub Issue is opened merely to duplicate this finding. Remediation begins
immediately through the evidence-driven framework change path.