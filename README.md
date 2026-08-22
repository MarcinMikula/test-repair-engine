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

**Sprint 3 — independent dynamic validation complete for the current
`data-testid` locator-recovery capability.**

The existing recovery path has now been exercised against the frozen PhoenixQA
Chaos App across official LOW, MEDIUM and HIGH configurations. Sprint 3 found one
real Playwright candidate-collection defect at LOW, preserved and corrected it,
then validated MEDIUM and HIGH without additional product tuning or LLM calls.

Current implementation includes:

- installable Python package,
- strict repair contracts,
- exact opaque ProjectProfile identity compatible with the current
  TestCartographer naming boundary,
- deterministic `data-testid` candidate ranking,
- action compatibility checks for `fill` and `click`,
- bounded Playwright candidate collection,
- explicit deterministic states for no candidate, weak evidence, bounded
  ambiguity, too-broad ambiguity and unique selection,
- an opt-in local Ollama fallback only for bounded 2–3 candidate ambiguity,
- exact local validation of the model response before execution,
- at most one model call and at most one browser retry,
- opt-in pytest runtime integration,
- final pytest outcome correlation,
- versioned `RepairRecord` JSON persistence with auditable LLM evidence,
- unit tests, controlled real-browser proofs and unchanged-framework acceptance,
- independent dynamic browser validation against PhoenixQA LOW/MEDIUM/HIGH,
- CI quality and browser-repair jobs.

The LLM is not a general healer. Deterministic logic decides whether the model is
eligible to act and re-validates any proposed replacement before a browser side
effect.

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

### Sprint 0 — complete

Executable project skeleton and ecosystem contracts.

### Sprint 1 — complete

Deterministic `data-testid` locator recovery and unchanged-test validation.

### Sprint 2 — complete

Bounded local Ollama fallback for deterministic 2–3 candidate ambiguity,
auditable LLM evidence, one-shot runtime execution and unchanged-framework
acceptance.

### Sprint 3 — complete

Independent dynamic validation of the existing `data-testid` recovery capability
against frozen PhoenixQA LOW/MEDIUM/HIGH. One real collector defect was found at
LOW, preserved, corrected and retested. MEDIUM and HIGH required no LLM
escalation; HIGH timing noise was handled by native Playwright waiting.

### Later validation directions

- broader locator families only when real evidence justifies them,
- timing/actionability recovery only when native Playwright behavior is genuinely
  insufficient in a useful real failure,
- stronger machine or human escalation only when lower tiers cannot resolve a
  well-evidenced problem safely,
- externally controlled / enterprise application coverage,
- pytest-xdist/process-safe correlation,
- durable maintenance remaining outside TestRepairEngine runtime ownership.

## License

MIT
