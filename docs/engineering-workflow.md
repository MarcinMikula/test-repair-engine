# Engineering workflow

## Purpose

This is the lightweight operating workflow for TestRepairEngine work performed
with a human and an LLM/agent.

It does not replace architecture, testing strategy, acceptance evidence, or
SDLC/STLC. It makes the recurring execution discipline explicit so a fresh agent
can work consistently without relying on chat history.

## 1. Bound non-trivial work

Before a larger capability slice, write a short change brief.

A brief is warranted when work materially changes product capability, recovery
authority, architecture, persisted evidence semantics, an external provider
boundary, or an acceptance maturity level.

A typo, EOF correction, obvious mechanical refactor, or evidence-only wording
update does not need a formal brief.

The brief may live in the current issue, sprint plan, or working conversation.
Persist it as a dedicated artifact only when later sessions need it as a durable
source.

### Change brief

```text
Problem
- What real problem are we solving?

Expected behavior
- What externally observable behavior should become true?

Scope
- What is included?

Out of scope
- What adjacent work is explicitly excluded?

Seam
- Through which public/runtime boundary should this be tested?

Acceptance oracle
- What independent observable result decides whether it works?

Authority / escalation
- Which tier may act?
- What requires abstention or human decision?

Evidence plan
- What must be preserved before and after the change?
```

Prefer an existing seam to a new one. Do not create an abstraction merely to make
a test easier.

### Qualification gate before implementation

For a suspected capability gap, safety boundary or recovery family,
qualification comes before product implementation.

Qualification means:

```text
define failure class
-> define risk
-> identify the real seam
-> define an independent oracle
-> freeze the relevant product/target boundary
-> exercise the failure without the proposed correction
-> classify ownership and competent authority tier
-> decide whether a real gap exists
```

Qualification is **not** implementation.

A valid qualification may conclude that behavior is already correct, native
Playwright is sufficient, the current tier safely abstains, evidence is
inconclusive, the gap belongs elsewhere, or a planned implementation is
`NOT REQUIRED`.

Stop before implementation when the observed failure is wrong, the oracle is
unclear, evidence conflicts, the required tier is unsupported, or the proposed
change crosses ecosystem ownership without evidence.

Only after a gap is qualified should a product/integration correction enter the
RED loop below.

## 2. Diagnose material bugs with a RED loop

Use:

```text
reproduce
-> preserve RED
-> minimise + classify
-> hypotheses when diagnosis is ambiguous
-> regression at the correct seam
-> smallest fix
-> focused GREEN
-> same original repro
-> broader regression/acceptance gate
```

### Reproduce

For a new capability/safety gap, enter this RED loop only after qualification
has established that correction is required.

Build the tightest practical feedback loop that detects the exact reported
symptom. Prefer, in order:

1. focused unit/integration test at the correct seam;
2. focused real-browser E2E;
3. bounded CLI or external acceptance harness;
4. manual/HITL reproduction only when automation cannot reach the boundary.

A nearby failure is not the same bug.

### Preserve RED

Before a product correction, preserve the first material evidence-bearing failure
when it reveals a real product boundary.

Capture enough identity to distinguish product revision, target revision, runtime
configuration, scenario/probe identity, the original failure, and which
recovery/model mechanisms actually ran.

A corrected run gets a new identity. Never overwrite the failed run.

### Minimise and classify

Reduce the scenario without changing the failure being investigated, then
classify the evidence as:

- product defect;
- validation-harness defect;
- target-semantics mismatch;
- environment/runtime-configuration problem;
- insufficient or contradictory evidence.

Do not change product code until the evidence supports a product defect.

### Hypotheses

For a hard or ambiguous diagnosis, write 3–5 ranked falsifiable hypotheses. Each
must predict an observable result.

Skip ceremonial hypotheses when direct evidence already isolates one simple cause.

### Regression and fix

Add a regression test before the fix when a correct seam exists. The regression
must exercise the real bug pattern, not a shallow imitation that can pass while
the original failure remains.

Apply the smallest justified fix, then run:

1. focused regression;
2. the original un-minimised reproduction;
3. the relevant broader gate.

A new green unit test alone does not close the defect.

## 3. Validate for evidence, not green output

For recovery validation:

- prove fail-before when recovery is the capability under test;
- keep the original test and assertions as the acceptance oracle;
- freeze source revision and relevant runtime configuration;
- prove the claimed mechanism was exercised, not merely configured;
- preserve safe abstention and intermediate tier failures;
- do not change thresholds, prompt, target, or oracle inside the same evidence run
  merely to rescue it;
- escalate only when the previous tier is insufficient and the next tier is
  competent to act;
- prefer native Playwright/framework behavior when it already solves the
  condition correctly;
- limit claims to the strongest evidence actually obtained.

The default authority order is:

```text
native Playwright/framework behavior
-> deterministic/heuristic TRE recovery
-> bounded local LLM assistance
-> human authority when evidence is insufficient, contradictory, or risky
```

The human line is an authority boundary, not a claim that the current TRE runtime
implements a human-review workflow. Stop when a lower tier is sufficient.

## 4. Implement in bounded vertical slices

Prefer a small slice that produces one complete, independently verifiable
behavior/evidence result.

Do not add speculative capability because a later slice was planned. Planned
LLM, correction, or healing slices may end as `NOT REQUIRED` when evidence does
not justify them.

## 5. Review on two independent axes

Before commit or PR, review the diff twice.

### Axis A — Spec / Intent

Check:

- the stated problem is actually solved;
- expected external behavior is implemented;
- in-scope work is complete;
- out-of-scope work did not leak in;
- the intended seam is still the exercised seam;
- the acceptance oracle remains independent and unchanged;
- authority, retry budget, LLM scope, and public claims did not widen without
  explicit justification;
- recorded evidence/verdicts match the actual run.

A clean implementation of the wrong requirement fails this axis.

### Axis B — Engineering / Standards

Check:

- architecture and ecosystem ownership are respected;
- terminology matches `CONTEXT.md`;
- the change sits at the smallest appropriate seam;
- tests verify behavior rather than irrelevant internals;
- runtime/provider/evidence states are represented truthfully;
- sensitive runtime values are not persisted;
- relevant lint/format/compile/unit/E2E gates pass;
- `git diff --check` passes;
- only intended files are changed and staged;
- parallel documentation did not become stale.

For a changed public status, capability, sprint boundary, or claim, search the
repository for old wording/status before commit.

A behaviorally correct change that violates the project contract fails this axis.

Both axes must independently pass, or carry an explicit accepted finding, before
commit/PR.

## 6. Commit and PR

Before commit:

- pin branch/base;
- inspect changed-file scope;
- run relevant quality gates;
- complete both review axes.

Keep large/local acceptance artifacts outside the repository unless the
repository explicitly owns them.

A PR should explain the change, reason, validation outcome, claim boundary, and
whether runtime/product behavior changed.

Keep local run IDs in acceptance/evidence documentation rather than filling
public PR prose with identifiers an external reviewer cannot open.

## 7. Findings, Issues, and learnings

Create durable artifacts only when they earn their maintenance cost.

- **Finding:** evidence must survive before remediation.
- **GitHub Issue:** evidence creates actionable work that should be tracked.
- **LEARNINGS.md:** evidence changes a reusable engineering rule or project
  understanding.

Do not create an Issue, ADR, learning, or research document merely because the
workflow has a place for one. Persist external research only when its findings
materially support a durable project decision that cannot be reconstructed
cheaply from the primary source.

## 8. Handoff only at a real context boundary

Use a handoff when moving to a new session/person/agent, pausing a large effort,
or crossing a boundary where the next session needs operational state not stored
elsewhere.

A handoff is an index, not another knowledge base.

```text
Current goal
Repository state
Completed work needed to understand the frontier
Authoritative repo sources
Open decision / next action
Local evidence locations, if needed
```

Reference existing specs, findings, Issues, PRs, and docs instead of copying them.

## 9. Closure

A slice closes when its oracle has been evaluated, material failures are
preserved, required regressions pass, both review axes are complete, claim scope
matches evidence, and any learning/Issue justified by the result is recorded.

Valid closure states include `PASS`, `FAIL`, and `NOT REQUIRED`. Green is not the
only useful result.
