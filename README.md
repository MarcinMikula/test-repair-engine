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

**Sprint 7 closed - locator-repair eligibility and redirection safety are now
validated across controlled browser evidence, frozen PhoenixQA, live Toolshop,
and the final merged-main integration.**

The current runtime remains deliberately narrow. TestRepairEngine recovers
logical Playwright `TEST_ID` locator drift, with `data-testid` as the default
physical attribute and an explicitly supplied custom Playwright test-id attribute
when required.

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
- fail-closed protection against actionability-to-locator redirection,
- independent PhoenixQA, Toolshop and merged-main validation.

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

Automatically recover common technical failures in Playwright tests and provide
validated repair evidence for durable maintenance by TestCartographer.

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

### Current frontier

The next capability is not pre-authorized merely because another sprint starts.
New work begins with qualification: define failure class, risk, seam, oracle,
ownership and supported authority tier, then prove a real gap exists before
product implementation.

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
