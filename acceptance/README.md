# Acceptance evidence

This directory preserves evidence-driven TestRepairEngine validation findings and
their closure state across independent runtime validation.

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
- Closing a finding records both the original failure evidence and the separate
  post-fix proof; closure never rewrites the historical failure.

## Findings

| Finding | Status | Pre-fix evidence | Post-fix evidence | Summary |
|---|---|---|---|---|
| [`TRE-FIND-001`](findings/TRE-FIND-001.md) | CLOSED | `run-20260820T165756Z` | `run-20260822T064419Z` | Real Playwright candidate collection dropped the rotated login button after an editability probe error; the narrow collector correction preserves the button as `editable=False`, and the unchanged LOW browser flow now recovers deterministically without LLM use. |

## Current Sprint 3 validation chain

```text
S3.1 stable target preflight
-> PASS: run-20260820T163217Z

S3.2-A LOW / TRE OFF
-> PASS: run-20260820T165244Z
-> selector rotation proved
-> original locators fail before repair

S3.2-B LOW / TRE ON / LLM OFF — pre-fix
-> FAIL: run-20260820T165756Z
-> username recovered heuristically
-> password recovered heuristically
-> btn-login candidate lost before useful ranking
-> TRE-FIND-001 opened and preserved

TRE-FIND-001 remediation
-> correction commit: 5c8f50048f06bd2612ec89280cbad0847d5d5bda
-> PR #6 merged
-> corrected main: 5e4ae946cf9cad197aace1d223c2383c5a085601
-> scoring / thresholds / ambiguity / LLM policy unchanged

S3.2-B LOW / TRE ON / LLM OFF — post-fix
-> PASS: run-20260822T064419Z
-> all three original locators fail naturally first
-> username -> username-xq1x | heuristic | score 0.678571
-> password -> password-l1pp | heuristic | score 0.678571
-> btn-login -> btn-login-pxbz | heuristic | score 0.801449
-> business oracle "Welcome, admin." PASS
-> LLM calls 0
-> PhoenixQA healer unused
-> TRE-FIND-001 closure criteria satisfied
```

## S3.2 LOW conclusion

The LOW selector-rotation validation is now complete with both failure and
correction evidence preserved.

The original `run-20260820T165756Z` remains the authoritative pre-fix failure.
The separate `run-20260822T064419Z` proves the corrected behavior on the same
frozen PhoenixQA commit and the same business oracle.

The validated correction is bounded to candidate collection: an editability
probe error no longer removes an otherwise valid click candidate before
deterministic ranking.

No broader healing claim is implied.

The next Sprint 3 validation step is:

```text
S3.3 — MEDIUM selector drift + DOM mutation
```
