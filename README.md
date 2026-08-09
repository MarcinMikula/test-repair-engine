# TestRepairEngine

> Runtime recovery for broken Playwright tests.

**TestRepairEngine** is a focused test-maintenance component for Python,
pytest, and Playwright automation.

Its job is deliberately narrow:

> Detect the broken interaction, repair it, rerun it, and let the original
> test prove the fix.

The project prioritizes practical repair effectiveness, low operational cost,
and simple integration over research into whether a particular recovery
mechanism is theoretically necessary.

## Status

**Sprint 0 — project skeleton and ecosystem contracts.**

Current capabilities:

- installable Python package,
- strict repair contracts,
- optional TestCartographer traceability,
- versioned `RepairRecord`,
- deterministic JSON persistence,
- unit tests and CI.

Runtime repair is **not implemented yet**.

The first functional slice will repair one broken Playwright locator and allow
the unchanged original test to continue.

## Ecosystem role

TestRepairEngine is designed as one module in a wider test-automation lifecycle:

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

- detect a failed technical interaction,
- identify a repair candidate,
- retry the failed interaction,
- allow the original test to continue,
- record what was repaired and how.

### TestCartographer

Owns broader engineering and durable maintenance:

- application and process context,
- accepted element knowledge,
- repository adaptation,
- re-observation,
- maintenance decisions,
- durable updates to framework content.

TestRepairEngine does not replace TestCartographer and does not own persistent
application knowledge.

## Product goal

Automatically recover common technical failures in Playwright tests and provide
validated repair evidence for durable maintenance by TestCartographer.

## Design principles

### Repair the smallest failure

TestRepairEngine should repair the failed technical interaction rather than
rewrite an entire test or Page Object.

### The original test remains the oracle

A recovered interaction is not enough to declare success.

```text
failed interaction
-> runtime recovery
-> original test continues
-> original assertions execute
-> final pytest result
```

Runtime recovery and final test success are separate facts.

### Cheap recovery before expensive recovery

The intended v0.1 order is:

```text
deterministic / heuristic repair
-> LLM fallback only when needed
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

### Loose ecosystem coupling

TestRepairEngine must work without importing TestCartographer.

When available, TestCartographer identifiers may be carried as opaque
traceability metadata in a `RepairRecord`.

## v0.1 scope

The first product version focuses on:

- Python 3.11+,
- pytest,
- Playwright,
- UI automation,
- locator drift,
- `click` and `fill` interactions,
- deterministic/heuristic repair first,
- local Ollama fallback later.

Out of scope for the initial slice:

- API/SOM repair,
- assertion repair,
- business-rule repair,
- automatic expected-result changes,
- automatic test-data correction,
- arbitrary source-code rewriting,
- autonomous application-defect diagnosis.

## Repair evidence

A successful runtime repair produces a versioned `RepairRecord`.

The record distinguishes:

```text
runtime_result
-> was the failed interaction recovered?

test_result
-> did the complete original test pass?
```

It may also carry optional references to the TestCartographer project and
context that existed when the repair happened.

TestRepairEngine does not interpret whether those references are still current.
That belongs to TestCartographer.

## Development

Create a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run quality checks:

```powershell
ruff check .
ruff format --check .
python -m compileall -q src tests
python -m pytest -m unit -v
```

## Roadmap

### Sprint 0

Executable project skeleton and ecosystem contracts.

### Sprint 1

Repair one controlled `data-testid` drift in `qa-automation-framework` using a
deterministic heuristic and prove:

```text
repair disabled
-> original test FAIL

repair enabled
-> failed interaction recovered
-> unchanged original test PASS
-> RepairRecord produced
```

### Sprint 2

Add Ollama as a fallback when deterministic candidate selection cannot resolve
the failure confidently.

## License

MIT
