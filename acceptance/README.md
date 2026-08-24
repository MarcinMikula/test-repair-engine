# Acceptance evidence

This directory preserves evidence-driven TestRepairEngine validation findings and
their closure state across independent runtime validation.

## Rules

- Preserve an evidence-bearing finding before implementing its correction.
- Historical browser runs remain immutable and are not rewritten after a fix.
- Large runtime artifacts stay outside the repository in
  `TestRepairEngine-local-artifacts`; committed findings reference their run IDs.
- A GitHub Issue may track remediation after the finding state is durable.
- A failed deterministic recovery must not be rescued by widening LLM authority,
  changing scoring thresholds, weakening the original test, or changing the target
  unless separate evidence justifies that change.
- Product correction and retest use a new commit and a new immutable run.
- Closing a finding records both the original failure evidence and the separate
  post-fix proof; closure never rewrites the historical failure.
- A failed recovery or acceptance run is a first-class validation result when it
  exposes a real product boundary, safe abstention or justified escalation. Do not
  tune a scenario only to obtain green output.
- A configured chaos mechanism is not sufficient acceptance evidence by itself;
  the tested flow must actually exercise the behavior behind the claim.
- Behavioral success with incorrect run/probe/RepairRecord provenance is useful
  diagnostic evidence, but it is not the authoritative acceptance record.

## Findings

| Finding | Status | Pre-fix evidence | Post-fix evidence | Summary |
|---|---|---|---|---|
| [`TRE-FIND-001`](findings/TRE-FIND-001.md) | CLOSED | `run-20260820T165756Z` | `run-20260822T064419Z` | Real Playwright candidate collection dropped the rotated login button after an editability probe error; the narrow collector correction preserves the button as `editable=False`, and the unchanged LOW browser flow now recovers deterministically without LLM use. |
| [`TRE-FIND-002`](findings/TRE-FIND-002.md) | CLOSED | `run-20260822T162252Z` | `run-20260822T171815Z` | Real Toolshop v4-to-v5 `data-test` drift exposed the physical test-id attribute collection gap; the correction was validated live with two deterministic recoveries, valid RepairRecords and zero LLM calls. |

## Sprint 3 validation chain

Frozen PhoenixQA target for the dynamic validation campaign:

```text
6e28811e37d9498a4d06237e1b26bf06b6159552
```

Authoritative browser runs used isolated `git archive` snapshots so ignored
local PhoenixQA `.env` state could not silently change the frozen runtime target.
PhoenixQA's own healer remained unused.

```text
S3.1 stable target preflight
-> PASS: run-20260820T163217Z

S3.2-A LOW / TRE OFF
-> PASS: run-20260820T165244Z
-> selector rotation proved
-> original locators fail before repair

S3.2-B LOW / TRE ON / LLM OFF â€” pre-fix
-> FAIL: run-20260820T165756Z
-> username recovered heuristically
-> password recovered heuristically
-> btn-login candidate lost before useful ranking
-> TRE-FIND-001 opened and preserved

TRE-FIND-001 remediation
-> correction commit: 5c8f50048f06bd2612ec89280cbad0847d5d5bda
-> PR #6 merged
-> corrected main: 5e4ae946cf9cad197aace1d223c2383c5a085601
-> scoring / thresholds / ambiguity / LLM policy unchanged

S3.2-B LOW / TRE ON / LLM OFF â€” post-fix
-> PASS: run-20260822T064419Z
-> username -> username-xq1x | heuristic | score 0.678571
-> password -> password-l1pp | heuristic | score 0.678571
-> btn-login -> btn-login-pxbz | heuristic | score 0.801449
-> business oracle "Welcome, admin." PASS
-> LLM calls 0

S3.3-A MEDIUM / TRE OFF
-> PASS: run-20260822T073152Z
-> selector_rotation + dom_mutation active
-> original login locators fail before repair

S3.3-B MEDIUM / TRE ON / LLM OFF
-> authoritative PASS: run-20260822T100403Z
-> username/password/btn-login recovered heuristically
-> business oracle "Welcome, admin." PASS
-> LLM calls 0
-> earlier run-20260822T080523Z retained as behavioral PASS only because
   stale helper provenance made it unsuitable as the authoritative record

S3.4-A HIGH / TRE OFF + timing proof
-> PASS: run-20260822T105112Z
-> selector_rotation + dom_mutation + async_delay active
-> AddItemForm confirmation hidden/absent after submit
-> confirmation appears after ~972 ms within native 3000 ms wait window
-> original username/password/btn-login/item-name/btn-add-item test IDs all broken

S3.4-B HIGH / TRE ON / LLM OFF
-> PASS: run-20260822T125113Z
-> five original locator interactions fail naturally first
-> all five recover heuristically
-> login oracle PASS
-> Add Item async delay exercised
-> native Playwright wait ~1886 ms PASS
-> TRE timing healing used: NO
-> Add Item oracle PASS
-> complete business flow PASS
-> LLM calls 0
-> repository changes NONE

S3.5 natural LLM escalation
-> NOT REQUIRED / NOT EARNED
-> no tested interaction reached bounded AMBIGUOUS

S3.6 additional correction after higher-level validation
-> NOT REQUIRED
-> MEDIUM/HIGH exposed no new product defect
```

## Sprint 3 conclusion

Sprint 3 is closed as independent dynamic validation of the existing narrow
`data-testid` locator-recovery capability.

The validation did not optimize for a sequence of green runs. LOW first exposed a
real product defect in candidate collection; that failure was preserved as
`TRE-FIND-001`, corrected separately and retested against the same frozen target.
MEDIUM and HIGH then passed without further product tuning.

The resulting recovery-tier evidence is:

```text
LOW
-> deterministic recovery sufficient after TRE-FIND-001 correction
-> LLM calls 0

MEDIUM
-> deterministic recovery sufficient while DOM mutation is active
-> LLM calls 0

HIGH
-> deterministic recovery sufficient for five broken data-testid interactions
-> native Playwright waiting sufficient for the exercised async delay
-> LLM calls 0
```

This supports a bounded claim only: current `data-testid` locator recovery
remained effective across the tested frozen PhoenixQA LOW/MEDIUM/HIGH flows.
MEDIUM/HIGH do **not** establish generic DOM-mutation healing or timing healing;
the latter was deliberately left to native Playwright waiting because it was
already sufficient.

A failed tier remains valid evidence and may justify escalation later. In Sprint
3, however, deterministic recovery never reached the bounded ambiguity state, so
an LLM call was not earned. No new Issue is opened merely to manufacture another
recovery tier or a green closure artifact.
---

## Sprint 5.1 pytest-xdist process-correlation qualification

Sprint 5.1 qualified the existing pytest runtime correlation boundary before
adding any new repair capability.

The product remained frozen at:

```text
f713a4299a23a569e3e16913cd669580c9885a55
```

`pytest-xdist` 3.8.0 was installed only into the local project environment for
qualification. It was not added to `pyproject.toml`, and no product source or
committed test was changed.

### Environment preflight lesson

The first pre-run attempt never became an S5.1 evidence run. The shell resolved
`python` to a user-installed Python 3.12 environment instead of the project
`.venv`; `pytest-xdist` was therefore installed outside the project environment
and the TestRepairEngine pytest entry point was unavailable.

The qualification stopped before creating an immutable run directory. The
environment boundary was corrected by proving `sys.executable` against
`.venv\Scripts\python.exe` before continuing.

### Attempt 1 - inconclusive harness oracle

```text
run-20260824T162324Z
```

Observed behavior:

- pytest produced the intentionally expected `1 passed, 1 failed`,
- exactly two RepairRecords were persisted,
- both runtime repairs were `recovered`,
- the passing test finalized as `test_result=passed`,
- the deliberately failing test finalized as `test_result=failed`,
- replacement locators were correct,
- repair IDs were distinct,
- LLM calls were zero,
- repository regression remained green,
- product source remained unchanged.

The run is **INCONCLUSIVE**, not a TestRepairEngine product failure.

Its oracle incorrectly required distinct TRE `run_id` values as proof of
different worker processes and assumed external qualification tests would expose
a file-qualified pytest node ID. The scheduler arrangement also did not directly
prove that the two active repairs ran in different worker processes.

The run remains immutable because it exposed a validation-harness defect and
still contains useful positive behavioral evidence.

### Attempt 2 - authoritative explicit-worker PASS

```text
run-20260824T163032Z
```

The corrected harness used explicit xdist worker identity and process markers.
The active scenarios were deliberately bound to separate workers:

```text
gw0
PID 3168
-> search-input -> catalog-search-input
-> runtime_result=recovered
-> test_result=passed

gw1
PID 16708
-> account-name -> account_name
-> runtime_result=recovered
-> test_result=failed
```

Both worker markers carried the same xdist test-run UID:

```text
d3c41dfd4af84d649a4e04e3905a178f
```

Authoritative evidence:

- explicit worker IDs were distinct: `gw0`, `gw1`,
- worker PIDs were distinct: `3168`, `16708`,
- both workers belonged to the same distributed xdist run,
- exactly two RepairRecords were written into one shared output directory,
- RepairRecord IDs were distinct,
- pytest node IDs were distinct and correctly correlated,
- records were explicitly bound to their worker scenarios,
- both runtime repairs were `recovered`,
- the `gw0` original test finalized as `passed`,
- the `gw1` original test finalized as `failed`,
- TRE process-local run IDs were distinct across the proven workers,
- no LLM call occurred,
- repository regression remained `100 passed`,
- Ruff format and lint checks passed,
- product changes were `NONE`,
- working tree remained clean.

### S5.1 conclusion

S5.1 found no product defect and therefore opened no `TRE-FIND-003`.

The bounded evidence supports only this claim:

> TestRepairEngine preserved independent RepairRecord and final pytest-result
> correlation for runtime repairs executed in two explicitly proven
> `pytest-xdist` worker processes sharing one RepairRecord output directory.

It does not yet establish general `pytest-xdist` support, high worker counts,
worker crash/restart recovery, heavy concurrent record volume, shared network
filesystems, xdist plus Ollama, or external/framework xdist acceptance.
