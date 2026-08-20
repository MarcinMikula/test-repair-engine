# TRE-FIND-001 — click candidate is lost during real Playwright collection, blocking LOW selector recovery

## Status

**OPEN — Sprint 3 product defect preserved before remediation.**

GitHub Issue: pending creation after the finding-preservation commit.

No product correction is authorized by this document alone.

## Discovery context

```text
validation slice: S3.2-B — LOW / TRE ON / LLM OFF
evidence-bearing run: run-20260820T165756Z

TestRepairEngine commit:
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
        └── run-20260820T165756Z/
```

The run directory is immutable pre-fix evidence and must not be reused or
rewritten.

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

## Observed behavior

S3.2-B run:

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

The final business oracle was not reached:

```text
business_oracle_passed = false
scenario_outcome = DETERMINISTIC_RECOVERY_NOT_PROVEN
```

Because the probe independently observed `btn-login-mj2x` immediately before the
interactions, the missing useful click candidate is not explained by selector
rotation failing to occur.

## Root cause

The current Playwright candidate collector evaluates several metadata properties
for every `[data-testid]` element inside one outer `try/except PlaywrightError`
boundary.

Relevant shape:

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

If one metadata probe raises `PlaywrightError`, the outer handler skips the
entire element.

For a valid click target such as `<button>`, editability is not required to
establish click compatibility. Allowing an editability probe failure to discard
the entire button therefore removes useful evidence before action filtering and
deterministic ranking.

The observed `btn-login` score of `0.078261` is consistent with the expected
`btn-login-mj2x` candidate being absent from the ranked click candidates even
though the page-level probe proved that element existed.

The defect boundary is therefore:

```text
non-essential metadata probe failure
-> whole valid click candidate discarded
-> deterministic ranker never sees expected rotated button
-> recovery fails below threshold
```

## Why existing tests did not catch it

`tests/unit/test_playwright_adapter.py` uses a `FakeElement` whose
`is_editable()` returns a boolean.

That test double proves deterministic selection behavior after a candidate has
been collected, but it does not model the real-browser failure shape where a
metadata probe can raise `PlaywrightError` for an otherwise valid click target.

Sprint 3's independently evolved browser target exposed this coverage gap.

## Classification

```text
kind:
product defect / candidate-collection defect

validation level:
Sprint 3 independent dynamic validation

severity:
blocks complete S3.2 LOW deterministic-recovery PASS

target defect:
false

PhoenixQA healer defect:
not evaluated / not used

LLM defect:
false

LLM escalation justified by this run:
false

historical evidence integrity:
preserved
```

## Why LLM escalation is not a correction

The failed click record says:

```text
llm_eligible = false
llm_called = false
```

This is correct.

The observed failure is not a bounded ambiguity requiring semantic choice. The
strong expected rotated button was removed before the deterministic ranking
boundary.

Enabling Ollama, weakening thresholds, or broadening LLM eligibility would mask
the collection defect and violate the recovery order:

```text
native Playwright
-> deterministic / heuristic TRE
-> bounded local LLM only for deterministic ambiguity
```

The correct response is to preserve valid candidate evidence.

## No-workaround rule

Do not make S3.2-B green by:

- enabling Ollama for this below-threshold result;
- lowering the deterministic score threshold;
- widening the ambiguity margin;
- changing `btn-login` in the original flow;
- using the observed rotated test id directly;
- modifying PhoenixQA selector rotation;
- using the PhoenixQA healer;
- weakening or replacing the business oracle;
- rewriting `run-20260820T165756Z`.

## Smallest correction boundary

The evidence justifies a narrow collector correction only:

1. Preserve a candidate when editability metadata is not applicable or its probe
   raises `PlaywrightError`.
2. Represent that candidate as `editable=False` rather than discarding it.
3. Add a regression test modeling a valid button whose editability probe raises.
4. Prove the button remains available to `RepairAction.CLICK` selection.
5. Do not change scoring, thresholds, ambiguity classification, retry budget,
   LLM eligibility, prompts, provider configuration, or PhoenixQA.

Candidate remediation branch after this finding is durable:

```text
fix/sprint-3-click-candidate-collection
```

## Acceptance criteria for closure

- [ ] A focused regression reproduces the real candidate-collection failure shape.
- [ ] A valid button candidate survives an editability-probe `PlaywrightError`.
- [ ] The candidate remains `editable=False` and available for click selection.
- [ ] Existing unit tests remain green.
- [ ] Static checks and full relevant regression suite pass.
- [ ] No scoring, threshold, ambiguity, LLM, or PhoenixQA change is required.
- [ ] S3.2-B is re-run against the same frozen PhoenixQA commit.
- [ ] Original `username`, `password`, and `btn-login` locators fail first.
- [ ] The repaired `btn-login` record identifies the real rotated `btn-login-xxxx`.
- [ ] `repair_method = heuristic`.
- [ ] LLM remains disabled and call count remains zero.
- [ ] The unchanged business oracle `Welcome, admin.` passes.
- [ ] A new post-fix immutable run is preserved.
- [ ] The pre-fix run `run-20260820T165756Z` remains unchanged.

## Retest rule

Do not reuse `run-20260820T165756Z`.

After the correction is separately implemented, reviewed, committed and
authorized for retest, execute the same S3.2-B scenario with:

- the same frozen PhoenixQA commit;
- the same official LOW selector-rotation configuration;
- the same original locators;
- TRE enabled;
- LLM disabled;
- the same final business oracle.

The retest must use a new immutable run directory and must be linked back to this
finding.
