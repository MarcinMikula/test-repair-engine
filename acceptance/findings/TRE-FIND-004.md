# TRE-FIND-004 - timeout actionability failures can redirect interactions while the original locator still resolves uniquely

## Status

**OPEN - evidence-qualified cross-layer safety gap.**

## Discovery context

Sprint 7 qualified the timeout/actionability boundary before authorizing any
product implementation.

The qualification used three evidence levels:

~~~text
S7.1
controlled real-browser cause matrix

S7.2
frozen PhoenixQA React/Vite real-application flow

S7.3
live external Practice Software Testing / Toolshop Angular flow
~~~

The finding is preserved before correction in accordance with the acceptance
workflow. Large runtime artifacts remain outside the repository under
`TestRepairEngine-local-artifacts`.

Frozen TestRepairEngine revision throughout qualification:

~~~text
2f5fc4946675096f42a016032750494a22bd713c
~~~

Frozen `qa-automation-framework` revision throughout qualification:

~~~text
a7f241cf1670668b88e2b38fe445dab8cd19daa0
~~~

Frozen PhoenixQA revision used by S7.2:

~~~text
9e01fe298ed2d72b3edd198d18bf3ac00c254232
~~~

LLM fallback remained disabled throughout all authoritative Sprint 7 evidence.

## Evidence chain

### Level 1 - S7.1 controlled browser matrix

Authoritative run:

~~~text
run-20260827T163820Z
QUALIFIED_ACTIONABILITY_REDIRECTION_RISK_CLICK_AND_FILL
~~~

S7.1 exercised nine controlled Playwright click/fill cases against the real
framework-to-TRE runtime seam.

Positive locator-drift control:

~~~text
original test ID:
save-action

original match count:
0

replacement:
primary-save-action

runtime_result:
recovered

test_result:
passed

LLM called:
false
~~~

Actionability failures without an alternative demonstrated broad timeout
delegation followed by safe deterministic abstention:

~~~text
click disabled original only
-> original count 1
-> original enabled false
-> TRE handoff
-> no candidate
-> runtime_result failed
-> original TimeoutError preserved

click blocked by overlay
-> original count 1
-> visible true
-> enabled true
-> pointer interception
-> TRE handoff
-> no candidate
-> runtime_result failed

click permanently hidden
-> original count 1
-> visible false
-> TRE handoff
-> no candidate
-> runtime_result failed

fill readonly original only
-> original count 1
-> editable false
-> TRE handoff
-> no candidate
-> runtime_result failed
~~~

Transient actionability controls proved that native Playwright remains first and
sufficient when the condition resolves inside the action timeout:

~~~text
transient visibility
-> native Playwright success
-> classifier calls 0
-> repair hook calls 0
-> RepairRecords 0

transient stability
-> native Playwright success
-> classifier calls 0
-> repair hook calls 0
-> RepairRecords 0
~~~

The safety gap appeared when a separate similar actionable candidate existed.

Click case:

~~~text
original:
save-action

original count:
1

original enabled:
false

alternative:
primary-save-action

observed physical interaction:
alternative

runtime_result:
recovered

test_result:
passed
~~~

Fill case:

~~~text
original:
account-name

original count:
1

original editable:
false

alternative:
account_name

alternative received value:
Marcin

runtime_result:
recovered

test_result:
passed
~~~

The original locators were not missing. They still resolved uniquely. The
failure cause was actionability, not locator drift.

### Level 2 - S7.2 frozen PhoenixQA real-application flow

Authoritative run:

~~~text
run-20260827T174917Z
QUALIFIED_REAL_APP_ACTIONABILITY_REDIRECTION_RISK_CLICK_AND_FILL
~~~

S7.2 repeated the qualified boundary against the frozen PhoenixQA Chaos App,
using the existing React/Vite login flow rather than isolated synthetic HTML.

Observed controls:

~~~text
normal login
-> NATIVE_BASELINE_PASS
-> TRE 0

selector rotation
-> REAL_APP_LOCATOR_DRIFT_RECOVERY

pointer-events overlay
-> DELEGATED_THEN_SAFE_ABSTAIN

permanent password invisibility
-> DELEGATED_THEN_SAFE_ABSTAIN

transient password visibility
-> NATIVE_PLAYWRIGHT_SUFFICIENT
-> TRE 0
~~~

The same two redirection risks reproduced inside the application flow:

~~~text
disabled original login button
+
similar enabled submit candidate
->
REDIRECTION_OBSERVED
->
business login PASS

readonly original password input
+
similar editable password candidate
->
REDIRECTION_OBSERVED
->
business login PASS
~~~

Therefore the S7.1 result was not limited to the isolated harness shape.

### Level 3 - S7.3 live external Toolshop acceptance

External target:

~~~text
https://practicesoftwaretesting.com/auth/login
~~~

The external application is live and mutable and therefore is not represented as
SHA-pinned. The evidence records its URL and runtime state separately from the
frozen TRE/framework revisions.

Toolshop exposes public automation hooks through `data-test`. The acceptance
harness mirrored those existing hook values one-to-one into `data-testid` on the
loaded DOM so the current framework-to-TRE integration could exercise the same
locator semantics without changing Toolshop source or business state.

First external attempt:

~~~text
run-20260827T180742Z
EXTERNAL_EVIDENCE_REQUIRES_REVIEW
~~~

That run remains immutable. Its T3 business login succeeded, but the harness
stored the physical-target marker only in `window` state. Successful navigation
to `My account` replaced the document and erased that marker, so the run
correctly remained review-only.

The corrected target oracle used navigation-persistent `sessionStorage` without
changing the scenario, candidate shape, TRE, framework, credentials or business
oracle.

Authoritative external run:

~~~text
run-20260827T181300Z
QUALIFIED_EXTERNAL_ACTIONABILITY_REDIRECTION_RISK_CLICK
~~~

Observed:

~~~text
T0 normal login
-> EXTERNAL_NATIVE_BASELINE_PASS

T1 controlled locator rename on the same physical submit element
-> EXTERNAL_LOCATOR_DRIFT_RECOVERY

T2 original login-submit still count 1 but disabled
-> EXTERNAL_DELEGATED_THEN_SAFE_ABSTAIN_DISABLED
-> original TimeoutError preserved

T3 original login-submit still count 1 but disabled
+
primary-login-submit enabled
->
EXTERNAL_REDIRECTION_OBSERVED_ORIGINAL_DISABLED
->
real Angular login business flow PASS
~~~

The external result confirms that the redirection risk is not confined to the
controlled matrix or the PhoenixQA benchmark target.

## Classification

This finding is an **evidence-qualified cross-layer safety gap with false-pass
risk**.

It is not a missing healing capability.

The current system can convert an actionability failure into a successful
interaction on a different element even when the original locator still resolves
exactly once.

The unsafe shape is:

~~~text
original test-id locator resolves exactly once
+
original element is not actionable
+
Playwright raises TimeoutError
+
framework delegates timeout to locator repair
+
similar actionable candidate exists
+
TRE selects the different locator
+
retry succeeds
+
unchanged business test can pass
~~~

A disabled button, readonly input, hidden control or pointer-intercepted control
may represent the real defect that the test is intended to expose. Locator
repair must not silently reinterpret that product state as locator drift merely
because Playwright surfaces the final failure as `TimeoutError`.

The risk is a false PASS: the test may appear green after performing the action
on a different physical target.

## Ownership

Ownership is **mixed, with primary responsibility at the framework handoff and a
required TestRepairEngine defense-in-depth boundary**.

### Primary - `qa-automation-framework`

The framework owns normal Playwright execution and the decision that a failed
interaction is eligible to enter the optional locator-repair path.

Current timeout behavior is too broad: a public `PlaywrightTimeoutError` is
sufficient to authorize TRE handoff even when the original locator still resolves
exactly once.

Sprint 7 evidence supports a narrower locator-repair eligibility distinction:

~~~text
TimeoutError
+
original test-id count == 0
->
locator-drift handoff may be justified

TimeoutError
+
original test-id count == 1
->
locator still resolves uniquely
->
do not treat the failure as locator drift
~~~

The strict-mode behavior qualified and corrected in `TRE-FIND-003` remains a
separate boundary:

~~~text
qualified strict-mode violation
+
original test-id count > 1
->
existing bounded strict-mode handoff remains eligible
~~~

Generic non-timeout Playwright errors must continue to remain outside repair
unless separately qualified.

### Defense in depth - TestRepairEngine

The framework guard is necessary but not sufficient.

`recover_test_id_action()` can be called from integration seams other than the
current `BasePage`. Once invoked, the current deterministic core can collect a
similar actionable candidate and retry it without independently proving that the
original test ID no longer resolves.

TRE therefore needs its own safety invariant:

~~~text
original test-id resolves exactly once
->
do not authorize locator substitution
->
no replacement retry
->
fail closed
~~~

This guard must apply independently to at least the already supported `CLICK` and
`FILL` actions.

The finding remains in the TestRepairEngine acceptance chain because Sprint 7
validated the ecosystem boundary and the eventual closure must prove both the
framework authorization rule and the engine defense-in-depth rule.

## Expected behavior

For the currently supported test-id click/fill recovery path:

1. native Playwright execution remains first;
2. transient actionability conditions that resolve inside Playwright's timeout
   remain native behavior and must not invoke TRE;
3. a timeout where the original test ID has zero matches may remain eligible for
   bounded locator-drift recovery;
4. a timeout where the original test ID resolves exactly once must not authorize
   locator substitution merely because that element is disabled, readonly,
   hidden, pointer-intercepted or otherwise non-actionable;
5. the qualified strict-mode multiple-match path from `TRE-FIND-003` remains
   intact;
6. TestRepairEngine itself must fail closed when invoked while the original test
   ID still resolves uniquely;
7. no `.first()`, `.last()`, `.nth()`, `force=True` or equivalent arbitrary
   selection may be introduced;
8. deterministic candidate scoring, thresholds and ambiguity policy remain
   unchanged unless separate evidence justifies a change;
9. LLM authority must not be widened to rescue a blocked deterministic safety
   decision;
10. runtime recovery remains distinct from final unchanged test success.

## Scope of correction

In scope:

- framework test-id timeout eligibility for `click_by_test_id` and
  `fill_by_test_id`;
- preservation of the existing qualified strict-mode multiple-match path;
- framework fail-closed behavior when original-locator state cannot be confirmed;
- TestRepairEngine defense-in-depth proof of original test-id match count before
  authorizing locator substitution;
- CLICK disabled-original plus candidate RED;
- FILL readonly-original plus candidate RED;
- positive zero-match locator-drift controls;
- focused and full regression;
- new immutable post-fix evidence at S7.1, S7.2 and S7.3 levels.

Out of scope:

- new locator families;
- scoring or threshold tuning;
- ambiguity policy changes;
- LLM expansion;
- retry-budget expansion;
- actionability healing such as forced clicks or waits;
- changing product state to make the original element actionable;
- RepairRecord schema expansion unless correction evidence proves it necessary;
- source rewriting or durable locator maintenance;
- TestCartographer behavior;
- API/SOM repair qualification.

## Acceptance basis

`TRE-FIND-004` may close only after separate correction evidence proves:

1. committed framework RED coverage shows that timeout plus original count `1`
   does not enter locator repair for representative CLICK and FILL actionability
   failures;
2. the existing zero-match timeout locator-drift path still enters TRE;
3. the existing qualified strict-mode multiple-match path remains green;
4. generic non-timeout Playwright-error protection remains green;
5. failed original-count confirmation fails closed;
6. committed TRE core RED coverage proves that direct
   `recover_test_id_action()` invocation cannot substitute a different locator
   while the original test ID still resolves exactly once;
7. TRE defense-in-depth covers both CLICK disabled-original plus candidate and
   FILL readonly-original plus candidate;
8. deterministic scoring, thresholds, ambiguity rules, retry budget and LLM
   authority remain unchanged;
9. S7.1 post-fix evidence preserves locator-drift recovery, native Playwright
   controls and safe actionability handling;
10. S7.2 post-fix evidence proves the frozen PhoenixQA login flow no longer
    redirects CLICK/FILL actionability failures while normal locator-drift
    recovery still works;
11. S7.3 post-fix external evidence proves the live Toolshop disabled-original
    case cannot redirect to the controlled alternate submit while the normal
    login and controlled locator-drift positive control remain valid;
12. all historical pre-fix and inconclusive/review runs remain immutable;
13. final product regressions remain green;
14. closure records exact correction commits, PRs, CI and authoritative post-fix
    run IDs.

## Current state

**OPEN.**

Qualification is complete. Product implementation has not started.

Next sequence:

~~~text
preserve TRE-FIND-004
-> merge finding evidence
-> framework RED
-> TRE defense-in-depth RED
-> smallest corrections
-> regression
-> S7.1 post-fix
-> S7.2 post-fix
-> S7.3 external post-fix
-> close TRE-FIND-004
~~~

No GitHub Issue is required merely to duplicate this durable repository finding.
