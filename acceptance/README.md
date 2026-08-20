# Acceptance evidence

This directory preserves evidence-driven TestRepairEngine validation findings that
must remain durable before remediation changes the product state.

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

## Findings

| Finding | Status | Evidence-bearing run | Summary |
|---|---|---|---|
| [`TRE-FIND-001`](findings/TRE-FIND-001.md) | OPEN | `run-20260820T165756Z` | Real Playwright candidate collection loses the rotated login button before deterministic ranking, blocking LOW selector recovery. |

## Current Sprint 3 validation chain

```text
S3.1 stable target preflight
-> PASS: run-20260820T163217Z

S3.2-A LOW / TRE OFF
-> PASS: run-20260820T165244Z
-> selector rotation proved
-> original locators fail before repair

S3.2-B LOW / TRE ON / LLM OFF
-> FAIL: run-20260820T165756Z
-> username recovered heuristically
-> password recovered heuristically
-> btn-login candidate lost before useful ranking
-> TRE-FIND-001
```

No Sprint 3 product correction is represented in this finding-preservation state.
