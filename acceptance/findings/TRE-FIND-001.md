# TRE-FIND-001 — click candidate is lost during real Playwright collection, blocking LOW selector recovery

## Status

**CLOSED — Sprint 3 product defect corrected and verified by an immutable post-fix browser retest.**

GitHub Issue: `#5`

The historical pre-fix failure remains authoritative evidence of the original
defect. Closure is based on a separate product correction and a separate post-fix
run; no historical evidence was rewritten.

## Discovery context

```text
validation slice: S3.2-B — LOW / TRE ON / LLM OFF
pre-fix evidence-bearing run: run-20260820T165756Z

pre-fix TestRepairEngine commit:
386cb70a4d47e5aa0da4785b6acfef843b72a86d

PhoenixQA commit:
6e28811e37d9498a4d06237e1b26bf06b6159552

target:
PhoenixQA Chaos App

runtime target isolation:
git archive of the frozen PhoenixQA commit
local ignored chaos_app/.env excluded

chaos level:
LOW

active level mechanism:
selector_rotation

PhoenixQA healer used:
false

TestRepairEngine LLM fallback:
disabled
```

The large browser evidence remains outside the repository at:

```text
TestRepairEngine-local-artifacts/
└── acceptance/
    └── s3.2-low/
        ├── run-20260820T165756Z/
        └── run-20260822T064419Z/
```

The first directory is immutable pre-fix evidence. The second directory is the
separate immutable post-fix retest.

## Validation chain before the finding

### S3.1 — stable target sanity

Authoritative run:

```text
run-20260820T163217Z
```

Result:

```text
stable config          PASS
original selectors     PASS
stable login           PASS
business oracle        PASS
TRE imported/executed  NO
PhoenixQA healer used  NO
repository changes     NONE
```

This established that the target and login flow work without chaos or recovery.

### S3.2-A — LOW / TRE OFF fail-before

Authoritative run:

```text
run-20260820T165244Z
```

Observed selector rotation:

```text
username   -> username-bznr
password   -> password-3frd
btn-login  -> btn-login-2eqd
```

All original locator counts were zero and the original `username` interaction
timed out as expected.

Result:

```text
official LOW                    PASS
selector_rotation               ACTIVE
original locators broken        CONFIRMED
expected Playwright timeout     CONFIRMED
TRE imported/executed           NO
PhoenixQA healer used           NO
repository changes              NONE
```

This proved a valid fail-before baseline before enabling TestRepairEngine.

## Expected behavior

S3.2-B changed only the recovery side:

```text
same frozen PhoenixQA LOW target
same original username/password/btn-login locators
same login credentials
same business oracle: "Welcome, admin."

TRE ON
LLM OFF
```

For each broken interaction the expected path was:

```text
original locator fails naturally in Playwright
-> TRE collects bounded current data-testid candidates
-> deterministic selection evaluates action-compatible candidates
-> unique strong candidate authorizes one retry
-> unchanged original business flow continues
```

For a direct rotated locator such as:

```text
btn-login
-> btn-login-xxxx
```

the expectation was deterministic heuristic recovery without any LLM call.

## Pre-fix observed behavior

Authoritative pre-fix S3.2-B run:

```text
run-20260820T165756Z
```

The page-level probe verified that all three rotated login ids existed before
the interactions:

```text
username   -> username-keve
password   -> password-zpa2
btn-login  -> btn-login-mj2x
```

The original locators all had count `0`.

Runtime recovery then produced:

```text
username:
  original timeout = true
  TRE recovered = true
  replacement = username-keve
  repair_method = heuristic
  selected_score = 0.678571
  candidate_count = 3
  llm_eligible = false
  llm_called = false

password:
  original timeout = true
  TRE recovered = true
  replacement = password-zpa2
  repair_method = heuristic
  selected_score = 0.678571
  candidate_count = 3
  llm_eligible = false
  llm_called = false

btn-login:
  original timeout = true
  TRE recovered = false
  replacement = null
  repair_method = null
  selected_score = 0.078261
  candidate_count = 3
  llm_eligible = false
  llm_called = false
```

The final business oracle did not pass:

```text
business_oracle_passed = false
scenario_outcome = DETERMINISTIC_RECOVERY_NOT_PROVEN
```

Because the probe independently observed `btn-login-mj2x` immediately before the
interactions, the missing useful click candidate was not explained by selector
rotation failing to occur.

This remains the authoritative evidence of the original defect.

## Root cause

The pre-fix Playwright candidate collector evaluated several metadata properties
for every `[data-testid]` element inside one outer `try/except PlaywrightError`
boundary.

Relevant pre-fix shape:

```python
test_id = element.get_attribute("data-testid")
tag_name = element.evaluate(...)
role = element.get_attribute("role")

LocatorCandidate(
    test_id=test_id,
    tag_name=str(tag_name),
    role=role,
    visible=element.is_visible(),
    enabled=element.is_enabled(),
    editable=element.is_editable(),
)
```

If one metadata probe raised `PlaywrightError`, the outer handler skipped the
entire element.

For a valid click target such as `<button>`, editability is not required to
establish click compatibility. Allowing an editability probe failure to discard
the entire button therefore removed useful evidence before action filtering and
deterministic ranking.

The observed pre-fix `btn-login` score of `0.078261` was consistent with the
expected `btn-login-mj2x` candidate being absent from the ranked click candidates
even though the page-level probe proved that element existed.

The defect boundary was:

```text
non-essential metadata probe failure
-> whole valid click candidate discarded
-> deterministic ranker never sees expected rotated button
-> recovery fails below threshold
```

## Why existing tests did not catch it

Before correction, `tests/unit/test_playwright_adapter.py` used a `FakeElement`
whose `is_editable()` returned a boolean.

That test double proved deterministic selection behavior after a candidate had
been collected, but it did not model the real-browser failure shape where a
metadata probe can raise `PlaywrightError` for an otherwise valid click target.

Sprint 3's independently evolved browser target exposed this coverage gap.

## Classification

```text
kind:
product defect / candidate-collection defect

validation level:
Sprint 3 independent dynamic validation

severity at discovery:
blocked complete S3.2 LOW deterministic-recovery PASS

target defect:
false

PhoenixQA healer defect:
not evaluated / not used

LLM defect:
false

LLM escalation justified by the failing run:
false

historical evidence integrity:
preserved

closure state:
corrected and verified by separate post-fix browser evidence
```

## Why LLM escalation was not a correction

The failed click record said:

```text
llm_eligible = false
llm_called = false
```

This was correct.

The observed failure was not a bounded ambiguity requiring semantic choice. The
strong expected rotated button was removed before the deterministic ranking
boundary.

Enabling Ollama, weakening thresholds, or broadening LLM eligibility would have
masked the collection defect and violated the recovery order:

```text
native Playwright
-> deterministic / heuristic TRE
-> bounded local LLM only for deterministic ambiguity
```

The correction therefore preserved valid candidate evidence instead of widening
model authority.

## No-workaround rule

The finding was not made green by:

- enabling Ollama for the below-threshold result;
- lowering the deterministic score threshold;
- widening the ambiguity margin;
- changing `btn-login` in the original flow;
- using the observed rotated test id directly;
- modifying PhoenixQA selector rotation;
- using the PhoenixQA healer;
- weakening or replacing the business oracle;
- rewriting `run-20260820T165756Z`.

These restrictions remained in force through the post-fix retest.

## Implemented correction

Correction branch:

```text
fix/sprint-3-click-candidate-collection
```

Correction commit:

```text
5c8f50048f06bd2612ec89280cbad0847d5d5bda
```

Merged by PR:

```text
#6 — fix: preserve non-editable click candidates
```

Resulting `main` merge commit:

```text
5e4ae946cf9cad197aace1d223c2383c5a085601
```

The correction is intentionally narrow:

1. visibility and enabled state continue to be collected normally;
2. `is_editable()` is probed separately;
3. an editability-probe `PlaywrightError` is normalized to `editable=False`;
4. the otherwise valid candidate is preserved;
5. the existing outer Playwright error boundary remains in place.

No change was made to:

- deterministic scoring;
- minimum score threshold;
- ambiguity margin;
- ambiguity classification;
- one-retry budget;
- LLM eligibility;
- LLM prompt;
- provider configuration;
- PhoenixQA target behavior.

## Regression coverage

The focused regression now models valid button candidates whose
`is_editable()` probe raises `PlaywrightError`.

It directly verifies:

```text
btn-login-a1b2    -> editable=false
btn-add-item-c3d4 -> editable=false
```

and then proves that `RepairAction.CLICK` deterministically recovers
`btn-login-a1b2` with heuristic selection and no LLM call.

Pre-merge local validation:

```text
tests/unit/test_playwright_adapter.py
15 passed

unit suite
93 passed, 5 deselected

ruff check
PASS

ruff format --check
PASS

python compileall
PASS

git diff --check
PASS
```

## Post-fix S3.2-B retest

Authoritative post-fix run:

```text
run-20260822T064419Z
```

TestRepairEngine baseline:

```text
5e4ae946cf9cad197aace1d223c2383c5a085601
```

PhoenixQA remained frozen at:

```text
6e28811e37d9498a4d06237e1b26bf06b6159552
```

Target isolation remained unchanged:

```text
git archive snapshot
archive SHA256:
77d30ce8fb2b4e71769df423abeec09e7ffc8ac561c2b9997828fe31f6c2bb66

local ignored chaos_app/.env included:
NO
```

The post-fix run used the same official `LOW` selector-rotation scenario, the
same original locators, the same credentials, TRE enabled, LLM disabled, no
PhoenixQA healer, and the same final business oracle.

Observed rotated ids:

```text
username   -> username-xq1x
password   -> password-l1pp
btn-login  -> btn-login-pxbz
```

All original selector counts remained zero:

```text
username   0
password   0
btn-login  0
```

Each original interaction timed out naturally before recovery.

Runtime recovery produced:

```text
username:
  original timeout = true
  TRE recovered = true
  replacement = username-xq1x
  repair_method = heuristic
  runtime_result = recovered
  test_result = passed
  selected_score = 0.678571
  candidate_count = 3
  llm_eligible = false
  llm_called = false

password:
  original timeout = true
  TRE recovered = true
  replacement = password-l1pp
  repair_method = heuristic
  runtime_result = recovered
  test_result = passed
  selected_score = 0.678571
  candidate_count = 3
  llm_eligible = false
  llm_called = false

btn-login:
  original timeout = true
  TRE recovered = true
  replacement = btn-login-pxbz
  repair_method = heuristic
  runtime_result = recovered
  test_result = passed
  selected_score = 0.801449
  candidate_count = 5
  llm_eligible = false
  llm_called = false
```

The increase from the pre-fix click candidate count of `3` to the post-fix count
of `5`, together with deterministic selection of the real rotated
`btn-login-pxbz`, is consistent with the corrected collector preserving valid
button candidates that previously disappeared before ranking.

Final result:

```text
scenario_outcome: DETERMINISTIC_RECOVERY_CONFIRMED
business_oracle_passed: true
repair_record_count: 3
LLM enabled: false
LLM calls: 0
PhoenixQA healer used: false
repository changes: NONE
S3.2-B verdict: PASS
```

The unchanged business oracle passed:

```text
Welcome, admin.
```

## Acceptance criteria for closure

- [x] A focused regression reproduces the real candidate-collection failure shape.
- [x] A valid button candidate survives an editability-probe `PlaywrightError`.
- [x] The candidate remains `editable=False` and available for click selection.
- [x] Existing unit tests remain green.
- [x] Static checks and full relevant regression suite pass.
- [x] No scoring, threshold, ambiguity, LLM, or PhoenixQA change was required.
- [x] S3.2-B was re-run against the same frozen PhoenixQA commit.
- [x] Original `username`, `password`, and `btn-login` locators failed first.
- [x] The repaired `btn-login` record identified the real rotated `btn-login-pxbz`.
- [x] `repair_method = heuristic`.
- [x] LLM remained disabled and call count remained zero.
- [x] The unchanged business oracle `Welcome, admin.` passed.
- [x] A new post-fix immutable run was preserved as `run-20260822T064419Z`.
- [x] The pre-fix run `run-20260820T165756Z` remains unchanged.

## Closure conclusion

`TRE-FIND-001` is closed.

The closure claim is bounded to the defect demonstrated by S3.2-B:

> A Playwright editability-probe error no longer causes an otherwise valid
> click candidate to disappear before deterministic ranking in the validated
> LOW selector-rotation scenario.

The finding does not claim broader support for new healing types, timing repair,
DOM mutation recovery, or general-purpose self-healing.

The next Sprint 3 validation step may proceed to the separately defined
`S3.3 — MEDIUM selector drift + DOM mutation` scope.
