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

**Sprint 1 — deterministic `data-testid` locator recovery.**

Current implementation includes:

- installable Python package,
- strict repair contracts,
- exact opaque ProjectProfile identity compatible with the current
  TestCartographer naming boundary,
- deterministic `data-testid` candidate ranking,
- action compatibility checks for `fill` and `click`,
- bounded Playwright candidate collection,
- one retry of the selected replacement,
- opt-in pytest runtime integration,
- final pytest outcome correlation,
- versioned `RepairRecord` JSON persistence,
- unit tests and a real-browser repair proof,
- CI quality and browser-repair jobs.

No LLM is used in Sprint 1.

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

If the evidence is weak or ambiguous, Sprint 1 returns control to the original
failure. Sprint 2 may ask a bounded local LLM only in such unresolved cases.

### Cheap recovery before expensive recovery

```text
deterministic / heuristic repair
-> LLM fallback later
-> escalation when repair cannot be validated
```

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

A Sprint 1 `RepairRecord` can contain:

- run ID,
- pytest node ID,
- action,
- locator kind,
- original test ID,
- replacement test ID when selected,
- heuristic repair method,
- bounded candidate count,
- selected deterministic score,
- runtime outcome,
- final pytest outcome,
- optional TestCartographer traceability.

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

## Sprint 1 acceptance

Repository-level implementation acceptance requires:

```text
unit suite                         PASS
real-browser baseline drift       reproduced
real-browser deterministic repair PASS
RepairRecord runtime_result       recovered
RepairRecord test_result          passed
```

The final Sprint 1 ecosystem gate additionally uses the unchanged
`qa-automation-framework` e-commerce test with a controlled search-input drift.
The framework integration is kept separate so the engine can be validated before
another repository is changed.

## Roadmap

### Sprint 0 — complete

Executable project skeleton and ecosystem contracts.

### Sprint 1 — current

Deterministic `data-testid` locator recovery and unchanged-test validation.

### Sprint 2

Add Ollama only when deterministic selection cannot resolve an otherwise
repairable locator failure safely.

## License

MIT
