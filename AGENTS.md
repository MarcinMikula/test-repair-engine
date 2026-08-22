# AGENTS.md

## Purpose

This file is the operating contract for an LLM or coding agent working in
TestRepairEngine.

It is a router, not a second README. Read the smallest authoritative source
needed for the task, preserve evidence before changing behavior, and prefer the
least powerful mechanism that solves the real problem safely.

## Start here

Before making a non-trivial change:

1. Read `CONTEXT.md` for canonical project terminology.
2. Identify the task type and read the matching source below.
3. Follow `docs/engineering-workflow.md`.
4. Pin the repository state and the intended scope before editing.

## Source routing

| Task | Read first |
|---|---|
| Product purpose, current public status, supported capability | `README.md` |
| Runtime boundaries, ownership, integration seams | `docs/architecture.md` |
| Test levels, acceptance strategy, escalation policy | `docs/testing-strategy.md` |
| Ecosystem ownership and cross-repository responsibilities | `docs/ecosystem-integration.md` |
| Validation findings, authoritative run chain, closure state | `acceptance/README.md` and relevant `acceptance/findings/*` |
| Why an important decision exists or what evidence changed our understanding | `LEARNINGS.md` |
| Project terminology | `CONTEXT.md` |
| How to plan, diagnose, review, hand off, and close work | `docs/engineering-workflow.md` |

Repository documents define the current contract; runtime artifacts record what
actually happened in a specific run. Neither should be rewritten to make the
other look correct. If they conflict, preserve the conflict and classify it.

Do not treat chat history, an old sprint plan, or an unreferenced local artifact
as a stronger source than the current repository contract.

## Non-negotiable engineering rules

- Preserve a real failure before correcting the product when the failure is
  material evidence.
- Treat failure, safe abstention, and justified escalation as valid validation
  outcomes.
- Keep the unchanged original test and its original assertions as the final
  acceptance oracle for runtime recovery.
- Repair the smallest technical interaction. Do not widen product authority to
  obtain a green result.
- Use native Playwright/framework behavior before TestRepairEngine recovery.
- Use deterministic recovery before bounded LLM assistance.
- Escalation must be earned by the observed failure state.
- Never call an LLM merely to demonstrate AI usage or to confirm an already safe
  deterministic decision.
- Keep `runtime_result` separate from `test_result`.
- Preserve historical evidence. A later PASS does not rewrite an earlier FAIL.
- Distinguish product defects from validation-harness defects, target semantics,
  and environment/runtime-configuration problems.
- A configured mechanism is not validated until the tested flow actually
  exercises it.
- Limit claims to the strongest capability and maturity level actually supported
  by evidence.
- Create or update a GitHub Issue only when evidence exposes an actionable
  defect, limitation, missing capability, or justified follow-up. Do not create
  Issues merely to mirror every sprint slice.
- Respect ecosystem ownership. Runtime recovery belongs here; durable application
  knowledge and maintenance decisions belong to TestCartographer.

## Default work sequence

For non-trivial work, use:

```text
intent / bounded change
-> test seam + acceptance oracle
-> RED / fail-before / evidence when applicable
-> classify
-> smallest implementation
-> focused regression
-> original scenario / broader gate
-> Spec/Intent review
-> Engineering/Standards review
-> commit / PR
-> acceptance evidence
-> learning / Issue only if deserved
-> closure
```

A trivial wording, formatting, or mechanical documentation correction may skip
the change brief and RED loop, but it still requires scope control and review.

## Stop conditions

Do not continue implementation when:

- the reproduced failure is not the failure the work intends to solve;
- the authoritative acceptance oracle is unclear;
- the next recovery tier is outside its documented competence;
- evidence is contradictory or insufficient for a safe automatic action;
- the change would cross an ecosystem ownership boundary without an explicit
  design decision.

In those cases, preserve what is known and escalate the decision to the human.
