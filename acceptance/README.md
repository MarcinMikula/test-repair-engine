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
| [`TRE-FIND-003`](findings/TRE-FIND-003.md) | CLOSED | `run-20260826T160742Z` + `run-20260826T161227Z` | `run-20260826T173922Z` | Real Playwright strict-mode multiple-match evidence exposed the framework timeout-only handoff gap; framework PR #2 added a narrow multiple-match classifier, and the real post-fix path recovered click/fill deterministically while duplicate-only evidence still failed closed with zero LLM calls. |
| [`TRE-FIND-004`](findings/TRE-FIND-004.md) | CLOSED | `run-20260827T163820Z` + `run-20260827T174917Z` + `run-20260827T181300Z` | `run-20260828T162811Z` + `run-20260828T163708Z` + `run-20260828T164909Z` + merged-main gate `run-20260828T171602Z` | Three-level qualification exposed actionability redirection false-pass risk; framework PR #3 now limits timeout handoff to missing test IDs, TRE PR #16 independently blocks substitution when the original test ID resolves uniquely, and controlled, PhoenixQA, live Toolshop and merged-main evidence preserve genuine locator-drift and strict-mode recovery while blocking CLICK/FILL redirection. |

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

---

## Sprint 6 strict-mode / multiple-match qualification

Sprint 6 began with TestRepairEngine product source frozen at:

```text
d1b5860849b7aa3d93846fa22834a31d278b8ad1
```

### S6.1 - framework handoff qualification

Authoritative run:

```text
run-20260826T160742Z
```

A real browser strict-mode case used two visible elements with the same original
`data-testid="save-action"`.

Observed:

```text
matching locator count      = 2
Playwright Error            = true
Playwright TimeoutError     = false
strict-mode violation       = true
framework repair hook calls = 0
strict RepairRecords        = 0
```

The same run proved the existing timeout path was active:

```text
save-action
-> catalog-save-action
-> repair hook calls 1
-> runtime_result recovered
-> test_result passed
-> LLM calls 0
```

Verdict:

```text
QUALIFIED_CAPABILITY_GAP
```

### S6.2 - deterministic core isolation

Authoritative run:

```text
run-20260826T161227Z
```

The unchanged TRE core was invoked explicitly after the already observed
strict-mode failure.

Duplicate-only case:

```text
save-action
save-action

collector candidates 2
ranked candidate_count 0
runtime_result failed
test_result failed
retry calls 0
LLM calls 0
```

This preserved safe fail-closed behavior.

Distinct-replacement case:

```text
save-action
save-action
primary-save-action

save-action
-> primary-save-action
-> heuristic
-> score 0.786667
-> runtime_result recovered
-> test_result passed
-> LLM calls 0
```

Verdict:

```text
QUALIFIED_HANDOFF_GAP_WITH_BOUNDED_CORE_PATH
```

Together, S6.1 and S6.2 isolate `TRE-FIND-003` to the framework interaction
handoff rather than the current deterministic TRE core.

The correction must remain narrow: generic non-timeout Playwright errors must not
become automatically repairable, and duplicate original test IDs alone must not
authorize arbitrary element selection.

### S6.3 - framework correction and post-fix closure

`TRE-FIND-003` was corrected at the framework interaction boundary, not in
TestRepairEngine product source.

Committed framework lineage:

```text
RED:
1b2b32e4072739083b384ccd1e2f851a7dc6ad8d

correction:
0cc9ee3909325eee99c39b4afbd329b178d919d4

style-only follow-up:
5c77a8235513e5dc202e4b8e343492eae1f3afb6

PR #2:
fix: delegate qualified strict-mode failures to TRE

merged framework main:
a7f241cf1670668b88e2b38fe445dab8cd19daa0

QA Framework Tests run #52:
success
```

The correction preserves the existing timeout path and generic non-timeout
Playwright-error protection. Strict-mode delegation is allowed only when the
error reports a strict mode violation and the current test-id locator still has
more than one match. Failed count confirmation remains fail-closed.

The first post-fix attempt is retained as non-authoritative evidence:

```text
run-20260826T173513Z
INCONCLUSIVE_HARNESS_FIXTURE_FAILURE
```

Its external harness depended on an unavailable pytest `page` fixture and
stopped before browser interaction.

Authoritative post-fix run:

```text
run-20260826T173922Z
PASSED / AUTHORITATIVE
```

Real browser/framework/TRE evidence:

```text
click
save-action
-> primary-save-action
-> heuristic
-> score 0.786667
-> runtime_result recovered
-> test_result passed

fill
account-name
-> account_name
-> heuristic
-> score 0.975
-> runtime_result recovered
-> test_result passed

duplicates only
save-action
save-action
-> no replacement
-> candidate_count 0
-> runtime_result failed
-> test_result failed
-> original strict-mode Playwright Error preserved

RepairRecords 3
LLM calls 0
```

The acceptance pytest result was deliberately:

```text
1 failed, 2 passed
```

The one failure is the required duplicate-only fail-closed oracle. It proves
that the corrected handoff does not authorize arbitrary selection among
duplicate original test IDs.

Regression gates:

```text
qa-automation-framework focused BasePage tests 23 passed
qa-automation-framework full unit suite        117 passed
TestRepairEngine full suite                    100 passed
TestRepairEngine Ruff                          PASS
repositories during acceptance                 CLEAN / FROZEN
```

Verdict:

```text
TRE-FIND-003 CLOSED
```

The bounded supported claim is now that framework test-id click/fill helpers may
delegate a qualified strict-mode multiple-match failure into the existing TRE
recovery path while generic non-timeout Playwright errors remain outside repair,
duplicate-only ambiguity remains fail-closed, and the unchanged original test
continues to own the final result.

---

## Sprint 8 ROLE_LINK semantic-repair qualification and closure

Sprint 8 expanded the validated locator boundary only after live evidence
justified a semantic slice that `TEST_ID` recovery could not represent safely.

The qualified authority is:

```text
locator family: ROLE_LINK
action: CLICK only

original exact accessible-name count == 0
-> build an anchored regex from all original alphanumeric tokens
-> retain every token, including duplicates, in original order
-> permit inserted content only between original tokens
-> require exactly one candidate
-> require candidate visible + enabled
-> retry one click
-> unchanged original test continues

zero candidates
multiple candidates
non-actionable unique candidate
original exact accessible name still resolves
probe / execution uncertainty
-> fail closed
```

The ROLE_LINK path is deterministic only. Sprint 8 did not authorize LLM use for
semantic locator repair and did not generalize authority to arbitrary roles,
buttons, fill actions, deletions, reorderings, prefix/suffix insertions, or broad
fuzzy accessible-name matching.

The final authoritative both-merged-main closure run is:

```text
run-20260829T181800Z
```

That run verified:

```text
TestRepairEngine full regression  -> 120 passed / Ruff PASS
qa-automation-framework full      -> 166 passed
framework ROLE_LINK focus         -> 7 passed
cross-repository positive control -> PASS
product changes during closure    -> NONE
```

No Sprint 8 finding was opened merely to mirror the new capability. The feature
was qualified, implemented through controlled RED -> GREEN history, validated
across both repositories, and then closed.

Post-closure hygiene was deliberately separate:

```text
framework PR #5
-> HYGIENE-01 / HYGIENE-02
-> wording + formatting only

TestRepairEngine PR #20
-> HYGIENE-03
-> wording only
```

Those hygiene changes did not alter the validated runtime behavior or reopen the
Sprint 8 acceptance claim.

---

## Sprint 10.1 release-consumer qualification

Sprint 10.1 qualified the existing product for release-style consumption before
any `0.1.0` version bump.

### S10.1A - clean wheel consumer

Authoritative closure:

```text
run-20260901T162800Z
```

The frozen TestRepairEngine source produced a normal wheel that was installed
non-editably into a fresh virtual environment. Import provenance, installed
distribution metadata, pytest entry-point metadata and actual pytest CLI plugin
discovery all passed.

Earlier attempts remain useful evidence of validation-harness/environment
failures rather than TestRepairEngine product failures:

```text
long Windows build path
-> wheel staging failure

native stderr handling
-> PowerShell harness interruption

fresh pip 24.0 certificate trust
-> dependency installation failure until system truststore was enabled

python -c quoting
-> malformed validation probe
```

None justified a product correction.

### S10.1B - installed TRE through frozen framework

Authoritative run:

```text
run-20260901T163319Z
```

Frozen identities:

```text
TestRepairEngine:
14cbf44352e01a2c450bcf7ecea558477e453396

qa-automation-framework:
522c1f7e597535ae0e541ec854200927234e7d5a
```

Runtime oracle:

```text
controlled drift:
search-input -> catalog-search-input

TRE OFF
-> unchanged framework test FAIL
-> Playwright timeout on search-input

TRE ON using installed wheel only
-> heuristic recovery
-> catalog-search-input
-> unchanged framework test PASS
-> one RepairRecord
-> runtime_result=recovered
-> test_result=passed
-> LLM calls 0
```

Both repositories remained unchanged and clean.

### S10.1 conclusion

```text
distribution consumer qualification -> PASS
framework consumer runtime           -> PASS
product correction                   -> NONE
new TRE finding                      -> NONE
```

S10.1 therefore closes as positive release-consumer evidence, not as defect
remediation.

---

## Sprint 10.3 permanent distribution-consumer CI gate

Sprint 10.3 converted the release-critical, repository-owned portion of S10.1
into a permanent CI boundary before the `0.1.0` release version bump.

The decision deliberately split two kinds of evidence:

```text
cheap repository-owned distribution/install proof
-> permanent TestRepairEngine CI

full frozen qa-automation-framework consumer runtime proof
-> acceptance/release evidence
-> not a regular cross-repository CI dependency
```

Implementation commit:

```text
c9ac412a8f0df0eeeac1df02edd786fbe11bef3c
```

PR #25 acceptance used GitHub Actions `tests` run #58. All five required jobs
passed:

```text
quality (3.11)                PASS
quality (3.12)                PASS
browser-repair                PASS
distribution-consumer (3.11)  PASS
distribution-consumer (3.12)  PASS
```

The new distribution jobs each exercised:

```text
build exactly one normal wheel
-> create fresh consumer venv
-> install wheel non-editably
-> pip check
-> leave repository working directory
-> import TRE from consumer site-packages
-> compare installed distribution version with pyproject metadata
-> require exactly one TRE pytest11 entry point
-> require test_repair_engine.pytest_plugin
-> invoke pytest --help from the consumer environment
-> require the installed TRE CLI options
```

After merge, main moved to:

```text
971d6acb09105238448272d3fefcfeec08fe2438
```

The independent push-triggered GitHub Actions `tests` run #59 then repeated the
same five-job matrix on merged `main`; all five jobs passed again.

Verdict:

```text
permanent distribution-consumer gate -> PASS
PR execution                         -> PASS
merged-main execution                -> PASS
runtime product correction           -> NONE
new TRE finding                      -> NONE
```

S10.3 therefore closes the release-facing CI decision required before the
`0.1.0` version bump.

---

## Post-release v0.1.0 quasi-UAT — published artifact consumer validation

**Review date:** 2026-09-03
**Status:** CLOSED / PASS
**Authoritative UAT run:** `run-20260903T170724Z`

This post-release validation asked a narrower product question than the release
qualification:

> Can the exact wheel published in GitHub Release `v0.1.0` be installed as a
> normal dependency beside the intended frozen framework consumer and recover
> the unchanged business test only when runtime repair is explicitly enabled?

The release was already formally published before this run. This campaign is
therefore additional product validation, not a retroactive release gate.

### Frozen boundaries

```text
TestRepairEngine main
399733cc8caf9a60fecd1629caf3fa3c60170566

qa-automation-framework main
522c1f7e597535ae0e541ec854200927234e7d5a

published wheel
test_repair_engine-0.1.0-py3-none-any.whl

published wheel SHA256
0fb657884bcd8d9719080d68730547879dc7be2981dc6680e6bc1228a4297428
```

The framework business test and Page Object remained unchanged throughout the
campaign. The controlled application seam changed only the search-input
`data-testid`:

```text
Page Object expects
search-input

controlled application state
catalog-search-input
```

### Validation chain

```text
Gate 1 — preflight
-> PASS
-> framework HEAD/origin-main exact and clean
-> consumer seam source blobs exact
-> published wheel downloaded from GitHub Release
-> wheel SHA256 exact
-> release manifest SHA256 exact

Gate 2 — healthy consumer baseline
-> PASS
-> fresh Python 3.12 consumer environment outside both repositories
-> frozen framework requirements installed
-> published TRE wheel installed non-editably
-> import provenance: consumer site-packages
-> pip check PASS
-> TRE pytest entry point discovered
-> Chromium ready
-> healthy application state
-> TRE installed but disabled
-> unchanged business E2E: 1 passed
-> RepairRecords: 0

Gate 3 — controlled fail-before
-> PASS as expected RED evidence
-> same framework / test / Page Object
-> application exposes catalog-search-input
-> TRE installed but disabled
-> unchanged business E2E: 1 failed
-> Playwright Locator.fill TimeoutError
-> waiting for get_by_test_id("search-input")
-> RepairRecords: 0
-> repository mutation: NONE

Gate 4 — controlled recovery
-> PASS
-> exact same drift and timeout as Gate 3
-> exact same framework / test / Page Object / published wheel
-> only authority change: --test-repair-engine
-> unchanged business E2E: 1 passed
-> exactly one finalized RepairRecord
```

The authoritative finalized RepairRecord reported:

```text
schema_version       0.2
action               fill
locator_kind         test_id
original_locator     search-input
replacement_locator  catalog-search-input
repair_method        heuristic
candidate_count      22
selected_score       0.791667
runtime_result       recovered
test_result          passed
LLM enabled          false
LLM eligible         false
LLM call_attempted   false
LLM outcome          not_called
```

This preserves the product's central result distinction:

```text
runtime interaction recovered
!=
test automatically accepted

runtime_result = recovered
-> unchanged original test continues
-> original assertions execute
-> test_result = passed
```

### Evidence preservation

The authoritative evidence bundle is stored outside the repository in accordance
with the acceptance rules:

```text
TestRepairEngine-local-artifacts/
└── post-release-v0.1.0-quasi-uat/
    └── run-20260903T170724Z/
```

It contains the published release assets, distribution probe, healthy baseline
output, controlled RED output, controlled GREEN output, the finalized
RepairRecord, an evidence summary and file hashes.

Three earlier evidence-closure verifier attempts stopped before bundle creation.
They were harness failures, not TestRepairEngine failures:

```text
v1
-> assumed UTF-8 when reading PowerShell-captured pytest text

v2
-> encoding heuristic still did not verify the real stored representation

v3
-> patching defect left the old UTF-8-only validation path active

v4
-> rebuilt verifier
-> checks required pytest markers against raw UTF-8/UTF-16 byte forms
-> validates RepairRecord and release hashes before creating the bundle
-> PASS
```

No product code, framework code, test, scoring rule, retry policy, LLM policy,
release artifact or repository state was changed to obtain the UAT PASS.

### Conclusion and park decision

The post-release quasi-UAT exposed no new TestRepairEngine product defect and
opened no new `TRE-FIND-*`.

The bounded claim is:

> The exact published TestRepairEngine `v0.1.0` wheel can be installed into a
> fresh environment beside the frozen intended framework consumer; with the
> tested controlled zero-match `TEST_ID + FILL` drift, TRE disabled preserves the
> original Playwright failure, while TRE enabled recovers deterministically once,
> records truthful evidence, and lets the unchanged business test determine the
> final PASS.

This does not establish arbitrary locator recovery, generic DOM repair, generic
actionability healing, unrestricted concurrency or universal application
compatibility.

With the first release, distribution gates and this post-release consumer
validation closed, active feature development on TestRepairEngine is now
**PARKED**. New TRE work should begin only from new evidence, a real consumer
problem, a security/maintenance obligation or another explicitly justified
requirement, and should enter a new SDLC slice rather than extending `v0.1.0`
speculatively.
