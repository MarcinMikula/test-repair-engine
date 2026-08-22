# Testing strategy

## Purpose

TestRepairEngine is judged primarily by whether it restores broken automation
without weakening the original test.

Testing therefore verifies both internal decision logic and real runtime
behavior.

## Quality objective

The central product question is:

> Can TestRepairEngine recover the failed technical interaction and allow the
> unchanged original test to pass?

## Test levels

### Unit

Fast deterministic tests cover:

- strict contracts,
- ProjectProfile traceability shape,
- locator tokenization and scoring,
- action compatibility,
- ambiguity abstention,
- Playwright adapter orchestration with bounded fakes,
- runtime repair registration,
- final test-outcome correlation,
- RepairRecord persistence and collision-safe immutability.

Unit tests start no browser and use no external model.

### E2E

Real Playwright execution is required for runtime-repair capability.

Sprint 1 contains two browser proofs against a controlled page:

```text
old search-input
new catalog-search-input
```

Baseline proof:

```text
repair not used
-> Playwright lookup/fill with search-input
-> timeout
```

Repair proof:

```text
current DOM contains catalog-search-input
-> deterministic candidate collection
-> fill compatibility filter
-> unique heuristic selection
-> retry succeeds
-> input contains original runtime value
-> RepairRecord runtime_result = recovered
-> finalized test_result = passed
```

The runtime value is used by the retry callback but is absent from persisted
repair evidence.

Sprint 2 adds a real-browser ambiguity proof with two close editable candidates:

```text
broken search-input
-> catalog-search-input
-> global-search-input
```

The controlled-browser validation proves three separate states:

```text
TRE disabled
-> original locator timeout

TRE enabled, LLM disabled
-> deterministic AMBIGUOUS
-> no provider call
-> original failure preserved

TRE enabled, bounded provider path
-> one validated shortlist selection
-> one real Playwright retry
-> original test continues
```

The real local-model run is kept separate from controlled provider tests so the
first Ollama observation can be preserved before any tuning.

### Ecosystem acceptance

Repository-level E2E proof is necessary but not sufficient for Sprint 2
acceptance.

The stronger acceptance uses the current `qa-automation-framework` e-commerce POM
flow because the product boundary sits below concrete Page Objects.

S2.8 runs the same existing checkout test with the same original assertions in
three configurations:

```text
unchanged EcommerceSearchPage expects search-input
controlled target exposes catalog-search-input
acceptance harness adds one competing editable global-search-input

TRE disabled
-> original framework test FAIL at search-input

TRE enabled, LLM disabled
-> deterministic bounded ambiguity
-> no provider call
-> original framework test FAIL closed

TRE enabled + real Ollama
-> one validated catalog-search-input proposal
-> one retry
-> original framework test continues unchanged
-> all existing assertions PASS
-> RepairRecord runtime_result = recovered
-> RepairRecord test_result = passed
```

The authoritative run is `run-20260819T171427Z`.

The controlled target drift and competing candidate belong to the external
acceptance setup. The framework source, TestRepairEngine source, target test and
its assertions remain unchanged.

## STLC alignment

Each runtime repair slice follows:

```text
test analysis
-> define one failure and expected recovery

test planning
-> define scope, environment, evidence and exit criteria

test design
-> define fail-before, pass-after, ambiguity and failure cases

environment preparation
-> prepare controlled Playwright target

test execution
-> run baseline and repaired scenarios

exit evaluation
-> verify original test and RepairRecord

closure
-> keep only evidence needed for maintenance
```

## Sprint 1 exit criteria

Sprint 1 is complete only when all applicable checks pass:

- package installs in a clean virtual environment,
- Ruff lint passes,
- Ruff format check passes,
- Python compilation passes,
- all unit tests pass,
- real-browser baseline proves old test ID failure,
- real-browser repair proves deterministic recovery,
- ambiguous deterministic candidates cause abstention,
- only one retry is performed,
- no LLM is called,
- no runtime input value is persisted,
- `RepairRecord.runtime_result` is `recovered`,
- `RepairRecord.test_result` is `passed` only after the original test completes,
- current framework flow fails with controlled drift when TRE is disabled,
- the same unchanged framework test passes when TRE is enabled.

## Sprint 2 exit criteria

Sprint 2 adds the following acceptance obligations:

- bounded ambiguity is a machine-readable deterministic state,
- only 2–3 candidate ambiguity is eligible for Ollama,
- deterministic winners, weak candidates and too-broad ambiguity never call the
  model,
- at most one Ollama call occurs for one failed interaction,
- provider timeout, transport failure, invalid JSON, invalid schema, abstention
  and outside-allowlist selection authorize no browser retry,
- a validated model selection is rechecked against the exact shortlist before
  execution,
- at most one browser retry occurs,
- `LLMEvidence` distinguishes enabled, eligible, called, response and outcome
  facts,
- `selected_score` is not attributed to an LLM decision,
- the first real-model observation is preserved before any tuning,
- the unchanged framework test fails with TRE disabled,
- the same unchanged framework test fails closed on deterministic ambiguity with
  LLM disabled,
- the same unchanged framework test passes after one validated real-Ollama
  selection,
- neither repository source nor the original test/assertions are changed to
  obtain the acceptance PASS.

## CI

The quality matrix runs on Python 3.11 and 3.12:

- editable installation,
- Ruff lint,
- Ruff format check,
- compileall,
- unit tests.

A separate Python 3.12 browser job installs Chromium and runs the E2E repair
slice. The `browser-repair` job is bounded to 30 minutes and the Chromium
installation step to 15 minutes so a stalled package mirror cannot leave the
validation pending for hours.

## Evidence integrity

Repair evidence is historical output, not scratch space.

Persistence must therefore fail closed when a destination already exists. A
second write must not replace an earlier RepairRecord, even if the caller
supplies the same destination accidentally. Regression coverage verifies that:

```text
existing RepairRecord
-> second write rejected
-> original bytes unchanged
-> temporary publish file removed
```

This is deliberately narrower than a general evidence-package system.
TestRepairEngine still owns individual runtime repair records, while broader
validation-run packaging and durable maintenance remain outside its runtime
scope.

## Machine-assisted and future actionability validation rules

Cross-project evidence from PhoenixQA establishes a useful authority boundary for
future TestRepairEngine slices:

```text
LLM proposal
-> deterministic validation against collected evidence
-> runtime action only when the bounded policy allows it
```

Model confidence or persuasive reasoning text is not execution authority.

For future timing/actionability recovery, evidence that a state *can* change
(such as a declared CSS transition or animation) must not automatically be
treated as evidence that the relevant state *is changing toward recovery*.
Observed temporal change is stronger evidence. The exact observation policy
remains future work and must be validated in TestRepairEngine before adoption.

### Sprint 2 machine-assisted contract rules

Cross-project acceptance findings from TestCartographer established stricter
rules for the bounded Ollama ambiguity fallback that Sprint 2 subsequently
implemented and validated.

The provider-facing contract, structured response parser, deterministic local
validation and execution allowlist must describe the same bounded decision space.
A model may select only a candidate that TRE supplied in the ambiguity shortlist;
it may not invent a replacement locator.

The runtime evidence must distinguish materially different LLM outcomes instead
of collapsing them into a generic "LLM failed" result. At minimum the Sprint 2
design must preserve enough information to tell apart:

```text
call failure
provider timeout
invalid JSON / parse failure
structured-contract or schema failure
explicit abstention
selection outside the supplied allowlist
validated selection
```

LLM usage metrics must be derived from actual runtime events. Enabling Ollama or
configuring a model does not count as a provider call.

Sprint 2 deliberately does not add an LLM repair/reflection loop:

```text
deterministic ambiguity
-> one Ollama proposal call
-> deterministic validation

validated selection
-> at most one runtime action retry

invalid / timed out / abstained / outside allowlist
-> preserve classified evidence
-> no second LLM call
-> original Playwright failure propagates
```

If abnormal test termination occurs after a repair attempt, persisted evidence
must not imply that the unchanged original test was successfully validated.
`test_result = unknown` remains acceptable until runtime evidence demonstrates
that a richer terminal-state contract is needed.

## Recovery escalation policy

TestRepairEngine is an engineering recovery component, not an LLM research
project. Validation must therefore prefer the least powerful mechanism that can
recover the failed interaction safely and preserve the original test oracle.

The default escalation order for future capabilities is:

```text
native Playwright / framework behavior
-> deterministic / heuristic TestRepairEngine recovery
-> bounded local LLM assistance
-> when local automation is insufficient:
   -> remote / online LLM when stronger machine reasoning is justified
   OR
   -> human review when domain, risk or evidence requires human authority
```

This policy does not mean that every runtime failure traverses every tier.
Escalation stops as soon as a lower tier has sufficient evidence.

In particular:

- if Playwright or the framework already handles a condition reliably, TRE must
  not add LLM-assisted recovery merely to demonstrate AI usage;
- if deterministic evidence selects a safe repair, the model must not be called
  only for confirmation;
- local LLM assistance is preferred before remote LLM use;
- failure of the local model should first trigger review of classification,
  collected evidence, logs, bounded context and task formulation;
- a larger/remote model is justified only when the evidence is already adequate,
  the local model remains materially insufficient, and the additional
  cost/data-transfer boundary is acceptable;
- human review is the terminal boundary when automated evidence cannot justify a
  safe action or when business/domain interpretation is required.

Remote LLM and human-review tiers are strategy boundaries, not claims that the
current runtime already implements them.

## Validation maturity

A healing capability is not considered broadly validated because one controlled
case passes. Each healing type should be exercised progressively against
difficulty levels that correspond to realistic application behavior.

The reusable maturity path is:

```text
controlled case
-> realistic ambiguity / dynamics
-> independently evolved target
-> unchanged business-flow oracle
```

The levels mean:

- **controlled case** — isolate the mechanism and prove fail-before / recover-after
  behavior in a bounded environment;
- **realistic ambiguity / dynamics** — introduce competing candidates, DOM
  mutation, timing or other behavior that can occur in real applications without
  manufacturing arbitrary complexity;
- **independently evolved target** — validate against a frontend whose structure
  was not designed specifically to make TRE pass;
- **unchanged business-flow oracle** — prove recovery through the supported
  framework path while the original test steps and assertions remain unchanged.

Not every healing capability must cross every maturity level in one sprint.
Documentation and product claims must state the strongest level actually
validated and keep broader levels explicitly unproven.

This maturity model applies across selector, visibility, timing/actionability and
future healing families. It is intended to improve engineering confidence, not to
turn TestRepairEngine into a benchmark of model intelligence.

Sprint 3 applied this strategy to the existing `data-testid` locator-recovery
capability against the independently evolved PhoenixQA Chaos App. LOW first
exposed a real candidate-collection defect that was preserved, corrected and
retested. MEDIUM and HIGH then validated the same locator-recovery capability in
the presence of DOM mutation and, at HIGH, a real asynchronous delay.

The HIGH delay did not justify a new timing-healing path because native Playwright
waiting was sufficient. Likewise, no tested LOW/MEDIUM/HIGH interaction reached
the bounded `AMBIGUOUS` state after the collector correction, so local LLM
escalation was not earned. These results validate the escalation policy; they do
not establish generic DOM-mutation healing or timing/actionability healing.

## Acceptance-basis evolution

TestRepairEngine acceptance requirements and test oracles are intentionally
incremental and evidence-driven rather than frozen before validation begins.

The initial basis should be sufficient to test the current bounded capability,
not an attempt to predict every future obligation. Controlled and later
nominal/external runs may expose a material gap that deserves a new or revised
requirement.

The evolution rule is:

```text
current test basis
-> real execution evidence
-> preserved finding / friction / abstention
-> requirement or oracle gap identified
-> smallest justified basis change
-> new coverage applied forward
```

This prevents two opposite failure modes:

- pretending the first requirement list was complete when real use proves it was
  not;
- moving the goalposts after every failure merely to make the product easier to
  accept.

A new or revised requirement therefore needs a defensible evidence reason.
Historical runs remain tied to the basis that existed when they were executed;
later requirements do not silently rewrite their original verdicts.

The process is deliberately lightweight and iterative. It keeps enough STLC
structure for traceability, independent retest and honest closure without turning
TRE validation into a permanently fixed corporate checklist.

### S2.8 acceptance-basis evolution

Framework acceptance exposed two verifier assumptions that are now part of the
test basis rather than product changes.

First, `candidate_count` is the count of all ranked action-compatible candidates,
not the length of the bounded ambiguity shortlist. Bounded LLM eligibility must
therefore be proven from deterministic ambiguity state/evidence and the actual
shortlist contract, not from `candidate_count == 2`.

Second, pytest-playwright parameterizes the runtime node ID, for example:

```text
tests/e2e/test_ecommerce_checkout_flow.py::TestEcommerceCheckoutFlow::test_customer_can_buy_available_product[chromium]
```

Acceptance correlation must preserve the real runtime node ID while recognizing
the intended base test identity. A verifier must not reject truthful evidence
merely because the supported browser parameter is present.

The S2.8 acceptance oracle is also now explicit:

```text
same original framework test
same original assertions

TRE OFF -> FAIL
TRE deterministic only -> bounded ambiguity -> FAIL closed
TRE + real Ollama -> one validated retry -> PASS
```

Correcting an evidence verifier after these assumptions were exposed does not
rewrite the original scenario execution. The original evidence run remains
immutable; corrected verification is appended as additional evidence.

## Anti-cheating invariants

A passing test is not accepted as a valid repair if TestRepairEngine achieved it
by:

- deleting or changing assertions,
- changing expected results,
- skipping the failing scenario step,
- replacing required test data merely to obtain PASS,
- using unrestricted forced interaction,
- retrying indefinitely.

## Deferred validation

Sprint 2 does not attempt to prove:

- general LLM robustness across diverse ambiguity shapes,
- behavior on independently evolved dynamic frontends,
- general selector healing beyond the current `data-testid` slice,
- timing/actionability repair,
- pytest-xdist/process-safe correlation,
- enterprise application coverage,
- automatic durable source updates.
