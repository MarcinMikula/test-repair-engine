# Context

Canonical domain language for TestRepairEngine.

This file is a glossary only. It does not contain sprint status, implementation
plans, architecture decisions, or historical reasoning. Those belong in the
sources referenced by `AGENTS.md`.

## Product and ecosystem terms

**TestRepairEngine (TRE)**

A bounded runtime-recovery component for failed technical interactions in
Playwright tests.

**qa-automation-framework**

The reusable execution host for Page Objects, Service Objects, pytest,
Playwright, assertions, fixtures, and normal reporting.

**TestCartographer**

The durable application-context and maintenance plane. It owns application
knowledge, provenance, re-observation, adaptation, and decisions about permanent
automation changes.

**PhoenixQA**

A broader experimental self-healing/R&D project. It may provide validation
targets and engineering lessons, but its healer is not TestRepairEngine.

**runtime recovery**

A bounded attempt to restore one failed technical interaction during test
execution.

**durable maintenance**

A persistent change to automation knowledge, framework content, or source after
runtime evidence has been reviewed. This is not owned by TRE runtime.

## Test and repair terms

**original test oracle**

The unchanged original test flow and its original assertions. A repaired
interaction is not accepted as a successful test until this oracle passes.

**failed interaction**

The smallest technical browser action that failed, such as one locator-based
`fill` or `click`.

**RepairRecord**

Versioned persisted evidence describing one repair attempt and its runtime/test
outcomes.

**runtime_result**

Outcome of the repair attempt itself, for example whether the failed interaction
was recovered. It is not the final test verdict.

**test_result**

Final correlated pytest outcome after the unchanged test continues. It is not
implied by a successful repair attempt.

**candidate**

An action-compatible runtime element considered as a possible replacement for a
broken locator.

**candidate_count**

The number of ranked action-compatible candidates considered by deterministic
selection. It is not the bounded LLM shortlist size.

**bounded ambiguity**

A deterministic selection state where 2–3 sufficiently plausible candidates
remain close enough that deterministic logic refuses to choose one winner.

**ambiguity shortlist**

The bounded 2–3 candidate subset supplied to the optional local LLM when, and
only when, deterministic classification makes the interaction LLM-eligible.

**LLM eligible**

Deterministic policy has classified the failure as one bounded ambiguity that the
configured LLM path is allowed to consider.

**LLM called**

A provider request actually occurred. `enabled`, `eligible`, `called`,
`responded`, `validated`, `retry executed`, and `test passed` are separate facts.

**fail closed**

Preserve the original failure path when available evidence cannot authorize a
safe bounded repair.

**recovery tier**

One level in the escalation order:

```text
native Playwright/framework behavior
-> deterministic/heuristic TRE recovery
-> bounded local LLM assistance
-> stronger machine or human decision only when separately justified
```

## Validation and evidence terms

**fail-before**

Evidence that the original interaction or scenario genuinely fails before the
repair under evaluation is applied.

**finding**

A durable repository record of evidence that exposed a material defect,
limitation, or validation-relevant boundary.

**GitHub Issue**

An actionable tracking item created when a finding or other evidence justifies
remediation or follow-up. A finding does not automatically require an Issue.

**authoritative evidence**

Evidence whose target, runtime configuration, identity, provenance, and scenario
match the acceptance basis strongly enough to support the project claim.

**behavioral evidence**

Useful observation of behavior that is not authoritative acceptance evidence,
for example because provenance or harness identity is wrong.

**frozen target**

A target whose source revision and relevant runtime configuration are controlled
for the validation claim. A clean Git worktree alone does not guarantee a frozen
runtime.

**configured mechanism**

A feature or chaos mechanism reported as enabled by configuration.

**exercised mechanism**

A configured mechanism whose behavior was actually reached and observed by the
tested flow. Configuration alone is weaker evidence.

## Failure classification terms

**product defect**

The product implementation violates its intended supported behavior.

**validation-harness defect**

The external script, verifier, probe, or acceptance orchestration is wrong while
the product behavior may be correct.

**target semantics**

The external target behaves differently from what the validation scenario
assumed; this may invalidate the scenario without implying a TRE defect.

**environment/runtime-configuration problem**

Execution state outside the product source, such as an ignored `.env`, process
environment, dependency/runtime issue, or stale local service, changes the
observed behavior.

These classifications are evidence categories. Do not convert one into another
merely because a different label makes the run easier to close.
