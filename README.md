# TestRepairEngine

> Runtime recovery for broken Playwright tests.

**TestRepairEngine** is a focused test-maintenance component for Python,
pytest, and Playwright automation.

Its job is deliberately narrow:

> Detect the broken interaction, repair it, rerun it, and let the original
> test prove the fix.

The project prioritizes practical repair effectiveness, low operational cost,
and simple integration over speculative repair taxonomies.

## Status

**Sprint 10 pre-release qualification through S10.3 is complete. The `0.1.0`
release candidate preserves the S10.1 clean-wheel and frozen-framework consumer
proof and adds the permanent S10.3 `distribution-consumer` CI matrix on Python
3.11 and 3.12. The PR gate and merged-main gate both built a normal wheel,
installed it non-editably into a clean consumer environment, verified installed
package provenance, distribution metadata, pytest entry-point registration and
CLI discovery, while the existing quality and browser-repair gates remained
green. No product correction or LLM call was required for the completed
pre-release qualification.**

Sprint 9 previously established the explicit Playwright interaction-scope
contract for `Page`, `Frame`, and `FrameLocator` without adding iframe
discovery or a new iframe-healing algorithm.

The current runtime remains deliberately narrow. TestRepairEngine recovers
qualified logical Playwright `TEST_ID` interaction failures: zero-match locator
drift and the separately qualified strict-mode multiple-match path.
`data-testid` remains the default physical attribute, with an explicitly
supplied custom Playwright test-id attribute when required.

TRE also supports one separately qualified semantic locator slice:
`ROLE_LINK` with `CLICK` only. It applies only when the original exact accessible
name no longer resolves, preserves every original alphanumeric token in order,
allows inserted content only between those tokens, requires exactly one
visible-and-enabled candidate, and fails closed otherwise. This path is
deterministic only; it does not use the LLM fallback.

The validated framework/TRE safety boundary is:

```text
normal Playwright action
-> success -> continue unchanged test

-> TimeoutError
   -> original test-id count == 0
      -> locator-drift handoff may enter TRE
   -> original test-id count == 1
      -> preserve original Playwright failure

-> qualified strict-mode violation
   -> original test-id count > 1
   -> bounded TRE handoff may run

-> generic non-timeout Playwright error
   -> preserve original failure
```

TRE also verifies the original test-id independently before substitution. Exact
original count `1`, or failure of that exact probe, fails closed. The probe is
independent of the bounded candidate shortlist.

Current validated implementation includes:

- installable Python package and opt-in pytest runtime integration,
- clean non-editable wheel installation and installed pytest-plugin discovery,
- frozen-framework consumer runtime proof using the installed wheel rather than
  TestRepairEngine source from a development checkout,
- strict contracts and immutable versioned RepairRecord persistence,
- deterministic logical `TEST_ID` candidate ranking,
- default `data-testid` plus explicit custom physical test-id attribute support,
- bounded candidate collection plus exact unbounded original-count protection,
- action compatibility for `fill` and `click`,
- explicit no-candidate / weak / ambiguity / too-broad / selected states,
- optional one-call Ollama fallback only for bounded 2-3 candidate ambiguity,
- exact local validation of model output before execution,
- at most one model call and at most one browser retry,
- final pytest result correlation,
- bounded two-worker pytest-xdist qualification,
- qualified strict-mode multiple-match framework handoff,
- bounded `ROLE_LINK` + `CLICK` accessible-name insertion recovery with a unique
  visible-and-enabled candidate and no LLM escalation,
- fail-closed protection against actionability-to-locator redirection,
- independent PhoenixQA, Toolshop and merged-main validation,
- explicit `PlaywrightInteractionScope = Page | Frame | FrameLocator` for the
  current runtime recovery entrypoints,
- framework-owned interaction-scope routing while Page lifecycle remains owned
  by the real outer `Page`,
- controlled branch-browser acceptance for both `Frame` and `FrameLocator`
  using `TEST_ID` + `FILL` and `ROLE_LINK` + `CLICK`, with finalized
  `RepairRecord.test_result=passed` and zero LLM calls.

Native Playwright/framework behavior remains first authority. The LLM is only a
bounded proposal mechanism, and the unchanged original test remains the final
oracle.

## Ecosystem role

```text
qa-automation-framework
        EXECUTES
           |
           | technical interaction failure
           v
TestRepairEngine
        RECOVERS
           |
           | RepairRecord
           v
TestCartographer
    UNDERSTANDS & EVOLVES
```

### qa-automation-framework

Owns normal automation execution:

- Page Objects and components,
- Service Objects,
- fixtures and test data bindings,
- pytest execution,
- Playwright execution,
- assertions,
- CI and normal reporting.

### TestRepairEngine

Owns bounded runtime recovery:

- inspect one failed technical interaction,
- collect minimal candidate metadata,
- select a deterministic replacement when evidence is strong enough,
- retry the failed interaction once,
- allow the unchanged original test to continue,
- record what was repaired and how,
- correlate the repair with the final pytest result.

### TestCartographer

Owns broader engineering and durable maintenance:

- project and application context,
- evidence and provenance,
- accepted element knowledge,
- re-observation,
- repository adaptation,
- maintenance decisions,
- durable updates to framework content.

TestRepairEngine does not import TestCartographer and does not decide whether a
runtime repair should become a permanent source change.

## Product goal

Recover qualified technical locator failures in Playwright tests when evidence
authorizes a safe bounded substitution, preserve the original failure when it
does not, and provide validated repair evidence for durable maintenance by
TestCartographer.

## Design principles

### Repair the smallest failure

TestRepairEngine repairs the failed technical interaction rather than rewriting
an entire test or Page Object.

### The original test remains the oracle

```text
failed interaction
-> runtime recovery
-> original test continues unchanged
-> original assertions execute
-> final pytest result
```

`runtime_result=RECOVERED` and `test_result=PASSED` are separate facts.

### Abstain on ambiguity

The deterministic selector does not choose merely because some candidate exists.
It requires:

- action-compatible structure,
- a minimum similarity score,
- a sufficient margin over the next candidate.

Weak evidence and too-broad ambiguity return control to the original failure.
Only a bounded 2–3 candidate ambiguity is eligible for the optional local Ollama
fallback, and a model selection still requires exact deterministic allowlist
validation before execution.

### Cheap recovery before expensive recovery

```text
native Playwright / framework behavior
-> deterministic / heuristic TestRepairEngine recovery
-> bounded Ollama fallback only for eligible ambiguity
-> fail closed when repair cannot be validated safely
```

The current runtime implements the deterministic tier and one bounded local
Ollama escalation path. More powerful automation is not invoked merely because a
lower tier failed; the failure state must justify the next tier.

Human review remains the intended terminal authority at the strategy boundary
when automated evidence cannot justify a safe repair. The current runtime does
not implement a human-review workflow.

### Do not make the test pass by weakening it

TestRepairEngine must not repair failures by:

- deleting assertions,
- weakening expected results,
- removing test steps,
- replacing expected test data,
- applying unrestricted `force=True`,
- retrying indefinitely.

## Sprint 1 repair slice

The first supported failure is controlled `data-testid` drift.

Example:

```text
Page Object expects:
search-input

application now exposes:
catalog-search-input
```

For a `fill` action, TestRepairEngine:

1. collects up to 50 elements carrying `data-testid`,
2. stores no input values, text, HTML, screenshots, or credentials,
3. rejects candidates that are not structurally compatible with `fill`,
4. ranks the remaining test IDs by token overlap and string similarity,
5. selects only a unique candidate above the configured deterministic gates,
6. retries the original fill once with the replacement test ID,
7. registers a `RepairRecord`,
8. lets pytest finish the unchanged original test,
9. persists `test_result=passed` or `failed` after teardown.

## Sprint 2 bounded LLM slice

Sprint 2 adds one narrow escalation path when deterministic ranking identifies a
bounded ambiguity instead of a unique winner.

```text
deterministic candidate classification
-> AMBIGUOUS with 2–3 close action-compatible candidates
-> optional one-call Ollama proposal
-> strict structured-response parsing
-> exact local shortlist allowlist validation
-> at most one retry
-> unchanged original test continues
```

The provider receives the bounded shortlist without deterministic scores. It may
select exactly one supplied candidate or abstain. Transport failure, timeout,
invalid JSON, schema mismatch, explicit abstention, outside-allowlist selection,
too-broad ambiguity and failed browser retry all fail closed.

Sprint 2 does not add reflection, a second judge, self-correction chat, a model
fallback chain or repeated repair attempts.

## Consumer installation

TestRepairEngine is designed to be consumed as an installed Python package,
not by placing its repository on `PYTHONPATH`.

For `v0.1.0`, the consumer artifact under release qualification is the wheel
built from the release source. A local wheel can be installed directly, for
example:

```powershell
python -m pip install path\to\test_repair_engine-0.1.0-py3-none-any.whl
```

Sprint 10.1 proved that a clean non-editable installation exposes the package
from consumer `site-packages`, registers exactly one
`test-repair-engine -> test_repair_engine.pytest_plugin` pytest entry point,
and works through the supported `qa-automation-framework` runtime seam.

Sprint 10.3 made the cheap distribution/install portion of that proof a
permanent CI gate on Python 3.11 and 3.12. The full frozen-framework consumer
runtime proof remains acceptance/release evidence rather than a regular
cross-repository CI dependency.

No PyPI installation path is claimed for `v0.1.0`.

## pytest activation

Installing the package registers a lightweight pytest plugin.

Runtime repair remains disabled unless explicitly enabled:

```powershell
python -m pytest --test-repair-engine
```

Repair records default to:

```text
repair-records/
```

A different directory may be selected with:

```powershell
python -m pytest `
    --test-repair-engine `
    --test-repair-record-dir artifacts/repair-records
```

When the flag is absent, TestRepairEngine does not attempt runtime repair.

## Repair evidence

A current `RepairRecord` (schema v0.2) can contain:

- run ID,
- pytest node ID,
- action,
- locator kind,
- original test ID,
- replacement test ID when selected,
- heuristic or LLM repair method,
- ranked action-compatible candidate count,
- selected deterministic score when the decision remained deterministic,
- runtime outcome,
- final pytest outcome,
- LLM evidence separating enabled, eligible, called, responded and provider
  outcome states,
- optional TestCartographer traceability.

`candidate_count` is the number of ranked action-compatible candidates. It is not
the size of the bounded LLM shortlist. The shortlist remains independently
limited to 2–3 candidates.

Runtime interaction values are deliberately absent.

## TestCartographer traceability

The optional project reference uses:

```text
project_profile_id
project_profile_revision
configuration_fingerprint
```

TestRepairEngine treats these values as opaque identity only. TestCartographer
owns compatibility decisions such as re-observation, repository resnapshot, or
review after project configuration changes.

## Development

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Install Chromium for the real-browser gate:

```powershell
python -m playwright install chromium
```

Run quality checks:

```powershell
ruff format .
ruff check .
ruff format --check .
python -m compileall -q src tests
python -m pytest -m unit -v
python -m pytest -m e2e -v
```

## Sprint 2 acceptance

Sprint 2 was accepted against the unchanged
`qa-automation-framework` e-commerce checkout test and its original assertions.

The accepted S2.8 sequence was:

```text
same original framework test
same original assertions

TRE OFF
-> FAIL at broken search-input

TRE ON, deterministic only
-> bounded ambiguity
-> no LLM call
-> FAIL closed

TRE ON + real Ollama
-> validated catalog-search-input selection
-> one retry
-> unchanged full framework test PASS
```

The authoritative framework-acceptance evidence run is
`run-20260819T171427Z`. No TestRepairEngine or framework product source was
changed to obtain the PASS.

This validates the supported framework integration for the bounded Sprint 2
slice. It does not establish general robustness across arbitrary locator
families, dynamic frontends or enterprise applications.

## Sprint 3 independent dynamic validation

Sprint 3 exercised the existing `data-testid` recovery capability against the
frozen PhoenixQA Chaos App commit:

```text
6e28811e37d9498a4d06237e1b26bf06b6159552
```

The campaign deliberately added no new healing type before observation.
Authoritative runtime evidence remained outside the repository under
`TestRepairEngine-local-artifacts`. PhoenixQA's own healer was disabled.

The evidence chain was:

```text
stable preflight
-> PASS

LOW selector rotation
-> fail-before confirmed
-> first deterministic run exposed TRE-FIND-001
-> narrow collector correction
-> unchanged LOW retest PASS

MEDIUM selector rotation + DOM mutation
-> fail-before confirmed
-> deterministic recovery PASS
-> LLM calls 0

HIGH selector rotation + DOM mutation + async delay
-> fail-before and real timing noise confirmed
-> five locator interactions recovered deterministically
-> native Playwright waiting handled the exercised async delay
-> complete business flow PASS
-> LLM calls 0
```

Authoritative MEDIUM recovery evidence is `run-20260822T100403Z`. Authoritative
HIGH fail-before/timing evidence is `run-20260822T105112Z`, and HIGH recovery
evidence is `run-20260822T125113Z`.

Sprint 3 therefore did **not** earn a natural LLM escalation slice. No tested
interaction reached the bounded `AMBIGUOUS` state after the LOW collector defect
was corrected. Calling Ollama only to demonstrate AI usage would contradict the
project's escalation policy.

The resulting claim remains bounded: current `data-testid` locator recovery was
validated across the tested PhoenixQA LOW/MEDIUM/HIGH flows. This does not claim
generic DOM-mutation healing, timing healing, arbitrary selector-family recovery
or enterprise-wide robustness.

## Roadmap

### Sprint 0 - complete

Established the executable package, strict contracts, deterministic JSON
evidence persistence, CI, ecosystem boundaries, and the rule that runtime
recovery is separate from final unchanged-test success.

### Sprint 1 - complete

Implemented conservative deterministic logical `TEST_ID` recovery with action
compatibility, score/margin gates, safe abstention, one retry, real-browser
fail-before/recover-after proof, and unchanged-test validation.

### Sprint 2 - complete

Added a bounded local Ollama fallback only for deterministic 2-3 candidate
ambiguity. Provider output is structured, locally allowlisted and revalidated
before any browser side effect.

Authoritative framework acceptance:
`run-20260819T171427Z`.

### Sprint 3 - complete

Validated locator recovery against frozen PhoenixQA LOW/MEDIUM/HIGH without
adding speculative healing. LOW exposed `TRE-FIND-001`, a real candidate
collection defect; the narrow correction was retested. MEDIUM and HIGH then
passed deterministically with zero LLM calls. Native Playwright waiting was
sufficient for the exercised HIGH async delay.

### Sprint 4.1 / 4.2 - complete

Live Toolshop v4/v5 evidence qualified historical test-id drift while Playwright
used `data-test`. `TRE-FIND-002` isolated the gap to the physical test-id
attribute. The adapter now keeps `data-testid` as default while accepting an
explicit custom attribute. Live post-fix recovery remained deterministic with
zero LLM calls.

### Sprint 5.1 - complete

Qualified the pytest runtime boundary with two explicitly proven pytest-xdist
worker processes sharing one RepairRecord directory. The first immutable run was
inconclusive because process identity was inferred; authoritative
`run-20260824T163032Z` recorded worker IDs/PIDs directly. No product correction
was required.

### Sprint 6 - complete

Qualified a strict-mode multiple-match integration gap before implementation.
S6.1 proved that real strict-mode failure bypassed the framework timeout-only
handoff. S6.2 proved the unchanged TRE core failed closed on duplicate-only
evidence and could recover only with a distinct safe replacement.

`TRE-FIND-003` was corrected at the framework seam with a narrow strict-mode
classifier. Generic non-timeout errors remain protected.

Authoritative post-fix:
`run-20260826T173922Z`.

### Sprint 7 - complete

Qualified and closed a cross-layer false-pass risk. Three independent pre-fix
levels proved that broad timeout delegation could redirect CLICK/FILL when the
original test-id still resolved uniquely but was non-actionable.

```text
S7.1 controlled browser matrix
-> CLICK + FILL risk

S7.2 frozen PhoenixQA
-> CLICK + FILL risk

S7.3 live Toolshop
-> CLICK risk
```

`TRE-FIND-004` introduced two independent boundaries:

```text
qa-automation-framework
-> TimeoutError enters locator repair only when original count == 0

TestRepairEngine
-> exact unbounded original-count probe before substitution
-> count == 1 or probe failure -> fail closed
```

Post-fix S7.1/S7.2/S7.3 blocked redirection while preserving zero-match drift and
the separately qualified strict-mode path.

Final merged-main gate:
`run-20260828T171602Z`
`VERIFIED_MERGED_MAIN_TRE_FIND_004_CLOSURE_GATE`.

### Sprint 8 - complete

Qualified and implemented one semantic locator family without generalizing TRE
into arbitrary role/name healing.

The supported authority is deliberately narrow:

```text
locator family: ROLE_LINK
action: CLICK
original exact accessible-name count: 0
candidate mechanism: anchored token-preserving insertion regex
candidate authority: exactly one visible + enabled match
LLM: not used
zero / multiple / non-actionable candidate: fail closed
```

The framework exposes this boundary through `click_by_role_link`. The unchanged
original test remains the final oracle.

Authoritative both-merged-main closure:
`run-20260829T181800Z`.

Post-closure hygiene changed documentation/formatting only and did not reopen the
validated runtime authority.

### Sprint 9 - complete

Sprint 9 did not begin with a pre-authorized iframe capability. Qualification
first asked whether the existing runtime had a real browsing-context gap.

The evidence chain was:

```text
S9.3 CONTROLLED
-> unchanged TRE recovered TEST_ID drift when given the correct Frame
-> top-level Page remained isolated
-> no new healer justified

S9.4 PUBLIC_EXTERNAL
-> the same behavior reproduced on a real public iframe structure
-> locator drift was controlled inside the browser session
-> this was not commercial validation

S9.5 CONTROLLED
-> FrameLocator supported both current TRE locator families
-> BasePage lifecycle methods were not a valid FrameLocator contract
-> interaction scope and Page lifecycle required separate ownership

S9.6 / S9.7
-> justified RED
-> explicit Page | Frame | FrameLocator interaction-scope contract
-> BasePage kept a real Page and gained optional interaction_scope
-> no repair algorithm or frame discovery added

S9.8
-> TRE 122/122 + full Ruff PASS
-> framework 169/169 after one classified transient Swagger timeout
-> cross-repository contract probe PASS

S9.9 CONTROLLED BRANCH ACCEPTANCE
-> Frame PASS
-> FrameLocator PASS
-> TEST_ID + FILL PASS
-> ROLE_LINK + CLICK PASS
-> 2 unchanged pytest tests PASS
-> 4 finalized RepairRecords with test_result=passed
-> LLM calls 0
```

The supported claim remains bounded: TRE can operate inside an explicitly
supplied Playwright `Page`, `Frame`, or `FrameLocator` interaction scope for its
already-qualified recovery families. TRE does not discover frames, choose a
browsing context, or claim general iframe healing.

Commercial / enterprise validation of this interaction-scope contract remains
outstanding.

### Sprint 10.1 - complete

Qualified the current product as a distributable consumer dependency without
changing TestRepairEngine or framework product source.

S10.1A authoritative clean-install closure:

```text
run-20260901T162800Z

frozen TRE source
-> wheel build
-> clean non-editable consumer venv
-> import from consumer site-packages
-> installed pytest entry point
-> pytest CLI plugin discovery
-> PASS
```

S10.1B authoritative framework-consumer runtime proof:

```text
run-20260901T163319Z

frozen qa-automation-framework snapshot
+ exact installed TRE wheel

TRE OFF
-> unchanged framework business test FAIL at search-input

TRE ON
-> search-input -> catalog-search-input
-> heuristic recovery
-> unchanged framework business test PASS
-> RepairRecord runtime_result=recovered
-> RepairRecord test_result=passed
-> LLM calls 0
```

The qualification found no TestRepairEngine product defect and required no
product correction.

### Current frontier

The runtime capability and release-facing distribution gate required for
`v0.1.0` are complete. The active frontier is release closure only:

```text
0.1.0 metadata
-> final five-job CI on the release candidate
-> merge to main
-> tag v0.1.0
-> GitHub Release
```

No new product capability is authorized before that release closure.

The next capability after `v0.1.0` is not pre-authorized merely because another
sprint starts. New work begins with qualification: define failure class, risk,
seam, oracle, ownership and supported authority tier, then prove a real gap
exists before product implementation.

Potential later directions:

- broader locator families only when evidence justifies them,
- timing/actionability healing only when native Playwright is genuinely
  insufficient for a useful real failure,
- stronger machine or human escalation only when lower tiers are insufficient,
- broader external/enterprise application coverage,
- broader pytest-xdist validation if support is intentionally promoted,
- API/SOM repair only after separate qualification,
- durable maintenance remaining outside TRE runtime ownership.

## License

MIT
