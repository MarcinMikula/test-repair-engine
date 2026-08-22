# TRE-FIND-002 — custom Playwright test-id attribute is invisible to candidate collection

## Status

**CLOSED — corrected and independently validated against the qualified live Toolshop drift.**

## Discovery context

Validation slice:

~~~text
S4.1 — Toolshop external historical locator-drift qualification
~~~

Authoritative qualification run:

~~~text
run-20260822T162252Z
~~~

Target:

~~~text
Practice Software Testing / Toolshop

v4:
https://v4.practicesoftwaretesting.com

v5:
https://practicesoftwaretesting.com
~~~

TestRepairEngine remained unchanged during qualification.

Playwright was explicitly configured to use:

~~~text
test-id attribute = data-test
~~~

No TestRepairEngine LLM fallback was used.

The large browser evidence remains outside the repository at:

~~~text
TestRepairEngine-local-artifacts/
└── acceptance/
    └── s4.1-toolshop-qualification/
        ├── run-20260822T160244Z/
        ├── run-20260822T161353Z/
        ├── run-20260822T161741Z/
        └── run-20260822T162252Z/
~~~

The earlier runs remain immutable validation-harness evidence. The final
qualification run is the authoritative S4.1 result.

## Real external locator evolution

The same Bank Transfer payment interaction exists in Toolshop v4 and v5, but its
test IDs changed during the application's evolution.

Observed in the live v4 payment form:

~~~text
account-name    count = 1
account_name    count = 0

account-number  count = 1
account_number  count = 0
~~~

Observed in the live v5 payment form:

~~~text
account-name    count = 0
account_name    count = 1

account-number  count = 0
account_number  count = 1
~~~

This is genuine external application evolution. The target was not modified to
manufacture locator drift.

## Observed TestRepairEngine boundary

With Playwright configured to use `data-test`, normal Playwright
`get_by_test_id()` semantics work against Toolshop.

The current TestRepairEngine collector returned:

~~~text
v4 candidate count = 0
v5 candidate count = 0
~~~

The current implementation scans only:

~~~text
[data-testid]
~~~

and reads only:

~~~text
data-testid
~~~

Therefore the existing TestRepairEngine `TEST_ID` recovery path cannot see
candidates exposed through a different Playwright test-id attribute.

## Deterministic capability behind the blocked collector

A qualification-only collector aligned to Toolshop's `data-test` attribute found
the live v5 candidates.

The unchanged production deterministic ranker selected:

~~~text
account-name
-> account_name
-> status: selected
-> score: 0.975

account-number
-> account_number
-> status: selected
-> score: 0.978571
~~~

No LLM call was required.

This isolates the gap to candidate collection semantics rather than scoring,
ambiguity handling or model reasoning.

## Classification

This finding is an **evidence-qualified capability gap**, not a regression
against the previously documented `data-testid`-only product boundary.

Real external evidence now justifies extending logical Playwright `TEST_ID`
recovery so callers can explicitly provide the physical test-id attribute used
by their Playwright configuration.

## Expected behavior

TestRepairEngine should preserve `data-testid` as the default physical test-id
attribute while allowing a caller to explicitly provide another Playwright
test-id attribute such as `data-test`.

Candidate collection must use that same attribute for both:

- locating candidate elements,
- reading candidate test-id values.

The recovery pipeline after collection must remain unchanged.

## Scope of correction

In scope:

- explicit custom test-id attribute at the Playwright adapter boundary,
- `data-testid` remains the backward-compatible default,
- candidate collection uses the supplied attribute,
- deterministic recovery continues through the existing ranking/retry path,
- regression coverage models the real `account-name` -> `account_name` drift.

Out of scope:

- new locator families,
- scoring changes,
- threshold changes,
- ambiguity-policy changes,
- broader LLM eligibility,
- remote LLM,
- additional browser retries,
- RepairRecord schema changes,
- timing/actionability healing,
- source-code rewriting,
- TestCartographer maintenance behavior.

## Acceptance basis

The correction is not closed by a green unit test alone.

Required proof:

1. a fail-before regression models custom Playwright test-id semantics;
2. the smallest adapter correction makes that regression pass;
3. existing default `data-testid` tests remain green;
4. the original Toolshop v4/v5 scenario is rerun as a new immutable post-fix run;
5. the unchanged deterministic ranker recovers the qualified locator drift;
6. no LLM call is required;
7. the original business interaction remains the final acceptance oracle.

## Closure

**CLOSED.**

Correction commit:

~~~text
6e6a3f6b383da7f1f6261fc423eeff630395bda8
feat: support custom Playwright test-id attribute
~~~

Authoritative pre-fix qualification:

~~~text
run-20260822T162252Z
~~~

Authoritative live post-fix acceptance:

~~~text
run-20260822T171815Z
~~~

The post-fix run re-exercised the real Toolshop payment interaction without
modifying the target application.

Observed historical contract:

~~~text
Toolshop v4

account-name    -> present
account-number  -> present
original fills  -> PASS
~~~

Observed current drift:

~~~text
Toolshop v5

account-name    -> absent
account_name    -> present

account-number  -> absent
account_number  -> present
~~~

Both old v5 locators naturally timed out before recovery.

The corrected production collector then inspected the explicitly configured
Playwright `data-test` attribute and saw both replacement candidates.

Production deterministic recovery produced:

~~~text
account-name
-> account_name
-> heuristic
-> score 0.975
-> runtime_result recovered
-> test_result passed

account-number
-> account_number
-> heuristic
-> score 0.978571
-> runtime_result recovered
-> test_result passed
~~~

Exactly two RepairRecords were produced. LLM fallback remained disabled and
no model call occurred.

The final interaction oracle confirmed the expected values in both recovered
fields. The acceptance stopped before order submission.

This closes the evidence-qualified capability gap.

The resulting claim remains bounded: the logical Playwright `TEST_ID` recovery
path now supports an explicitly supplied physical test-id attribute while
preserving `data-testid` as the default. This does not establish support for
arbitrary locator families, generic DOM healing, timing healing or unrestricted
selector inference.
