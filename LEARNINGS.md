# Learnings

Chronological engineering journal for TestRepairEngine.

This file preserves the reasoning behind decisions that matter beyond the current
implementation. Current product behavior belongs in `README.md` and `docs/`;
this file records what evidence changed our understanding and what consequence
should survive into later sprints.

---

## Sprint 0 — keep runtime recovery separate from durable maintenance

**Date:** 2026-08-09  
**Status:** Established

### Problem

The wider automation ecosystem already has distinct responsibilities:

```text
qa-automation-framework
→ executes tests

TestRepairEngine
→ restores a failed technical interaction at runtime

TestCartographer
→ owns application knowledge, review, adaptation and durable maintenance
```

A repair engine could easily become a second application model or source-code
maintenance system if those boundaries were not made explicit from the start.

### Decision

TestRepairEngine owns only bounded runtime recovery and repair evidence.

It may carry TestCartographer identifiers as opaque traceability, but it does not
interpret ProjectProfile compatibility, application knowledge or whether a
runtime repair should become a permanent source change.

Runtime recovery and final test success are separate facts. A repaired action is
not accepted as a successful test until the unchanged original test finishes and
its original assertions pass.

### Consequence

The first contracts separate `runtime_result` from `test_result`, keep
TestCartographer optional, and avoid a runtime package dependency between the two
projects.

---

## Sprint 1 — deterministic repair must be allowed to abstain

**Date:** 2026-08-10  
**Status:** Validated

### Problem

Choosing the most similar locator merely because one candidate ranks first would
turn heuristic recovery into guessing.

### Evidence

The first real-browser slice showed that a useful repair path can stay small:

```text
old locator: search-input
new locator: catalog-search-input
```

The engine can collect bounded structural metadata, reject candidates that do
not support the failed action, rank the remaining candidates and retry one
replacement. The unchanged framework test then provides the real acceptance
oracle.

### Decision

Candidate selection requires:

- action compatibility,
- a minimum similarity score,
- a sufficient margin over the second candidate.

Weak or ambiguous evidence causes abstention. Sprint 1 performs only one retry
and never weakens assertions, expected results or test data to obtain PASS.

### Consequence

The deterministic layer is intentionally conservative. A later LLM fallback is
useful only if it adds information at an ambiguity boundary that the cheap layer
correctly refuses to cross.

---

## Sprint 1 — integrate below concrete Page Objects

**Date:** 2026-08-10  
**Status:** Validated across repositories

### Problem

If concrete Page Objects knew about TestRepairEngine, runtime repair would leak
into application-facing automation code and make the framework dependent on the
repair module.

### Decision

The integration boundary belongs in a reusable mechanical interaction helper.
Normal Playwright behavior runs first; only a validated timeout may delegate to
an optional TestRepairEngine hook.

Concrete Page Objects and the original test remain unchanged.

### Consequence

With TestRepairEngine absent or disabled, framework behavior remains ordinary
Playwright behavior. Recovery is off the normal success path and the complete
original test remains the oracle.

---

## Cross-project lesson — controlled repair proof is not product validity

**Review date:** 2026-08-12  
**Source evidence:** TestCartographer Sprint 17 external-acceptance preflight

### New evidence from TestCartographer

After TestCartographer introduced a repeatable validation protocol, its first
external acceptance campaign exposed a product limitation before the external
site was exercised: the nominal Creation Flow was still coupled to the
project-controlled catalog fixture across target setup, discovery, synthesis and
delivery.

The important response was not to rescue the run. The finding was preserved and
the acceptance rules explicitly rejected monkeypatching, test-only fixture
substitution, manual internal-state repair, locator injection or direct runner
editing inside the same acceptance run.

A second limitation then appeared: the original four-page external scenario
required multi-page discovery that the product did not yet implement. Instead of
silently shrinking that historical test until it could pass, TestCartographer
kept it blocked and designed a separate smaller single-page acceptance case.

### Impact on TestRepairEngine

This does **not** require a runtime architecture change and does **not** justify
importing TestCartographer validation contracts into TestRepairEngine.

It does change how later TestRepairEngine acceptance should be interpreted:

1. Controlled demo targets are valid for deterministic implementation and
   regression proofs, but they do not by themselves establish general product
   validity.
2. A nominal acceptance run must use supported product/framework integration
   paths. It must not be made green by monkeypatching, locator injection,
   internal-state editing or other test-only surgery that bypasses the behavior
   being evaluated.
3. Fail-before, safe abstention and failed LLM decisions are evidence. Preserve
   them before changing heuristics, prompts, model configuration or integration
   behavior.
4. If a planned acceptance scenario requires an unsupported broader capability,
   record that limitation. Do not rewrite the historical scenario after seeing
   the blocker; create a smaller independent scenario when that is the honest
   next validation step.
5. A passing pytest result remains insufficient when the route to PASS bypassed
   the intended TestRepairEngine boundary or changed the original oracle.

### Consequence for Sprint 2+

The planned bounded Ollama ambiguity fallback remains technically valid.
However, its acceptance should distinguish:

```text
controlled target
→ proves fallback mechanics and regression safety

nominal/external acceptance later
→ tests whether the supported integration works without hidden rescue paths
```

If model or prompt tuning is needed after a failed run, the failed observation
should remain part of the evidence rather than being overwritten by the final
passing attempt.
