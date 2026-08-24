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

---

## Cross-project lesson — persisted repair evidence must fail closed on collision

**Review date:** 2026-08-14
**Source evidence:** TestCartographer Issue #5 (`ACC-FIND-005`)

### New evidence from TestCartographer

An external-acceptance run exposed destructive startup behavior in
TestCartographer: a pre-existing operator-supplied output directory was treated
as disposable and recursively removed before a new run started.

The filesystem stopped the operation with a permission error, but partial
deletion could already have occurred. The acceptance finding therefore treated
the run identifier as consumed/unsafe and required later runs to use new,
immutable output locations.

### Impact on TestRepairEngine

TestRepairEngine does not delete its repair-record directory and normally writes
UUID-named files, so it does not share the same bug directly.

Reviewing the analogous boundary exposed a smaller weakness: the Sprint 1 writer
published a temporary file with `replace()`. If a destination with the same
`repair_id` already existed, historical repair evidence could therefore be
silently replaced.

A UUID collision is unlikely, but evidence integrity should not depend on that
probability. Accidental reuse, replayed fixtures or future caller bugs should
fail closed.

### Decision

A RepairRecord destination is immutable once created.

Persistence now:

```text
serialize to a temporary file in the destination directory
→ publish only if the destination does not exist
→ collision raises FileExistsError
→ existing evidence remains byte-for-byte unchanged
→ temporary file is cleaned up
```

This remains an individual-record guarantee, not a new validation-package
subsystem.

---

## Cross-project lesson — PhoenixQA is R&D evidence for runtime healer design

**Review date:** 2026-08-14
**Source evidence:** PhoenixQA Sprint 6B (`RECEIVES_EVENTS`, `VISIBLE`)

PhoenixQA is intentionally broader and more experimental than TestRepairEngine,
but its validated failures and mechanisms are relevant input to TRE design. TRE
should reuse the lesson, not automatically copy the feature.

### LLM diagnosis is not execution authority

The live `RECEIVES_EVENTS` investigation showed a useful failure mode: the local
model correctly described a persistent blocker with no dismiss affordance, yet
still proposed `wait_and_retry`.

A deterministic policy checked structured collector evidence and corrected the
proposal to `no_safe_recovery`. The original Playwright failure then propagated
unchanged.

The important lesson for TRE Sprint 2 is:

```text
LLM proposes
→ deterministic boundary validates
→ only a validated bounded action may execute
```

Model confidence and reasoning text may be useful evidence, but they must not
become the authority that permits a runtime side effect.

### Declared capability is weaker than observed change

The later `VISIBLE` slice identified another evidence-design distinction before
shipping its policy: a CSS animation or transition declaration proves only that
change is possible, not that a relevant state is actually progressing toward
recovery.

PhoenixQA therefore moved the VISIBLE evidence shape toward two real browser
observations separated by wall-clock time and asks the deterministic policy
whether target state actually changed.

That principle is relevant to future TRE timing/actionability work, but the
current PhoenixQA VISIBLE slice is not yet live-verified end to end. TRE should
therefore preserve the lesson as a design constraint, not treat the exact
1200 ms observation implementation as validated reusable product logic.

---

## Cross-project lesson — machine-assisted boundaries need one complete contract

**Review date:** 2026-08-17
**Source evidence:** TestCartographer `ACC-FIND-006`, `ACC-FIND-011`, `ACC-FIND-012`; acceptance requirements v0.2 (`ACC-REQ-020`)

### New evidence from TestCartographer

Level 1/1B external validation exposed three related machine-assisted boundary
problems across separate real runs.

First, browser-discovery metrics counted one live LLM call merely because Ollama
mode was configured, even though no discovery guidance turn existed. The metric
described configuration rather than an observed runtime event.

Later, a target-proposal response parsed as valid JSON but failed the product
contract before human review. The first diagnostic was too generic to identify a
safe validation category or rule. After that boundary was made diagnosable and
bounded recovery was introduced, the next live run exposed a deeper mismatch:
the provider-facing schema, local action-conditioned validators and recovery
classifier did not represent the same complete contract.

This evidence is stronger than a theoretical concern because each limitation was
revealed by a real execution path after the previous blocker had been crossed.

### Impact on TestRepairEngine Sprint 2

The bounded Ollama ambiguity fallback must keep one consistent contract across:

```text
provider-facing prompt/schema
→ response parsing
→ deterministic local validation
→ execution allowlist
```

The model may select only from the candidate shortlist that TRE supplied. A
syntactically valid answer is not sufficient if it violates that bounded
contract.

LLM outcomes must also remain diagnostically distinguishable. Sprint 2 should be
able to tell apart at least:

```text
call failure
provider timeout
invalid JSON / parse failure
schema or structured-contract failure
explicit abstention
selection outside the supplied allowlist
validated selection
```

These are evidence states, not model-quality verdicts.

### Decision

1. The contract exposed to the provider must match the contract enforced by the
   deterministic runtime boundary.
2. LLM usage metrics must come from actual runtime events, not from provider
   configuration or an enabled feature flag.
3. An invalid LLM result does not start an LLM repair/reflection loop in TRE
   Sprint 2. The result is classified, preserved as bounded evidence and the
   original Playwright failure propagates.
4. Sprint 2 keeps one Ollama proposal call and at most one runtime action retry
   after deterministic validation.
5. If a RepairRecord remains after abnormal test termination, it must not imply
   that the unchanged original test was successfully validated. `test_result`
   may remain unknown until later evidence justifies a richer terminal-state
   contract.

This is a Sprint 2 design constraint, not authorization for code changes before
the sprint starts.

---

## Validation lesson — acceptance requirements evolve from execution evidence

**Review date:** 2026-08-17
**Source evidence:** TestCartographer acceptance requirements v0.2 and the findings that produced `ACC-REQ-018` through `ACC-REQ-020`

### Observation

TestCartographer did not attempt to predict every acceptance obligation before
external validation began. Its initial acceptance basis was deliberately
incomplete. Repeated real runs exposed material-intent preservation, truthful
persisted lifecycle and machine-assisted contract/recovery obligations strongly
enough to justify new explicit requirements.

The historical runs kept their original identities and verdicts. New
requirements were applied forward instead of being used to rewrite the meaning
of evidence that had already been collected.

### Decision for TestRepairEngine

TRE validation will use the same evidence-driven principle without copying
TestCartographer's requirement catalogue.

The acceptance basis is intentionally incremental:

```text
start with enough requirements to test the current bounded capability
→ execute real controlled and later nominal/external scenarios
→ preserve failures, abstentions and friction
→ identify a repeated or material requirement gap
→ add or revise the smallest justified requirement/test oracle
→ apply the new basis forward
```

Requirements are therefore not a frozen checklist created once and defended for
the rest of the project. That would be fragile for a small evolving product: the
initial basis may omit an important obligation, and real execution may expose a
better boundary than design discussion alone could predict.

At the same time, "incremental" does not mean moving the goalposts after every
failure. New or revised requirements need evidence and a clear reason. Historical
runs remain evaluated against the basis that existed when they were executed,
unless a later review explicitly states otherwise.

### Consequence

TestRepairEngine keeps a lightweight iterative validation model: enough structure
to preserve traceability and prevent self-rescue, but no requirement to maintain
a permanently fixed corporate-style acceptance catalogue before the product has
generated the evidence needed to deserve one.

---

## Sprint 2 — bounded Ollama ambiguity fallback, slice-by-slice validation record

**Review date:** 2026-08-19

**Status:** Validated through S2.8; S2.7 correction not required; S2.9 closure

**Frozen live-validation base:** `b3aae4128f5a24db8535dc991f5575d9ba840553`

Sprint 2 tested whether a local LLM can add value only at a deterministic ambiguity
boundary without becoming general execution authority. The work was deliberately
split into small slices so that classification, provider contract, evidence,
execution wiring, browser behavior and the first real model run could be
validated independently.

| Slice | What we wanted to verify | What we checked and how | Result | Learning |
|---|---|---|---|---|
| **S2.1 — bounded ambiguity classification** | The deterministic layer must distinguish a genuinely bounded ambiguity from no candidates, weak candidates, too-broad ambiguity and a unique deterministic winner. | Added explicit machine-readable selection statuses and a shortlist only for 2–3 close, action-compatible candidates. Unit tests exercised `NO_CANDIDATES`, `BELOW_THRESHOLD`, `AMBIGUOUS`, `AMBIGUOUS_TOO_BROAD` and `SELECTED`. Commit: `39bcfd7` (`feat: classify bounded locator ambiguity`). | **PASS.** Bounded ambiguity became an explicit state rather than an interpretation of reason text. | LLM eligibility must start from deterministic classification. A model must not be called merely because deterministic repair did not return a winner. |
| **S2.2 — strict Ollama decision contract** | One local model call must be unable to invent execution targets or expand its own authority. | Added a fixed local Ollama endpoint, a 2–3 candidate structured shortlist, a two-shape `select` / `abstain` response schema, duplicate-key rejection, exact allowlist validation, deterministic generation settings (`temperature=0`, `seed=42`) and distinct provider outcomes for transport, timeout, JSON, schema, abstention, allowlist and validated selection. The model does not receive deterministic candidate scores. Commit: `5ef539b` (`feat: add strict bounded Ollama decision contract`). | **PASS.** The provider can propose only one supplied candidate or abstain; it has no browser authority. | Provider-facing schema and deterministic enforcement must represent the same complete contract. Structured output is not trusted until local validation succeeds. |
| **S2.3 — auditable LLM runtime evidence** | Runtime evidence must distinguish configuration, eligibility, actual provider use and provider outcome instead of treating "LLM enabled" as "LLM used". | Added `LLMEvidence` and runtime configuration for opt-in LLM use. Evidence records `enabled`, `eligible`, `call_attempted`, `response_received`, provider, model, outcome and latency. RepairRecord schema moved to v0.2 while historical v0.1 remains readable. Unit and existing E2E regressions stayed green. Commit: `e1a21a9` (`feat: add auditable LLM runtime evidence`). | **PASS.** Evidence can state truthfully that LLM was enabled but not eligible/called, or that it was called and failed/abstained/validated. | `enabled != eligible != called != responded != validated != retry executed != test passed`. These facts must remain separate in persisted evidence. |
| **S2.4 — ambiguity → Ollama → deterministic validation → one browser retry** | Real runtime wiring must preserve deterministic precedence, call Ollama only for eligible ambiguity, fail closed on every invalid/non-selection outcome, and authorize at most one retry after exact local revalidation. | Wired `recover_test_id_action()` to the real provider boundary. Unit tests proved: deterministic winner → zero LLM calls; LLM disabled → zero calls; too-broad ambiguity → zero calls; valid model selection → one call and one retry; transport/timeout/invalid JSON/invalid schema/abstain/outside allowlist → no browser retry; inconsistent provider selection is rejected again at execution; failed browser retry is not retried again. A review fix also removed deterministic `selected_score` from records after any actual LLM call so heuristic ranking cannot be misrepresented as the model's decision evidence. Final gates: 92 unit tests passed and 2 E2E tests passed. Commit: `0ffc029` (`feat: wire bounded Ollama ambiguity recovery`). | **PASS.** S2.4 required no broad exception loop, model self-correction loop or second retry path. | LLM decision success and browser execution success are different facts. Defense in depth belongs at the execution boundary even when the provider already validated its response. |
| **S2.5 — controlled real-browser validation** | The S2.4 wiring must work against a real Chromium DOM, not only mocks, without changing product code to make the test pass. | Added one test-only E2E file using `page.set_content()` with broken `search-input` and two real editable candidates: `catalog-search-input` and `global-search-input`. Three proofs were executed: original locator really times out; deterministic-only ambiguity fails closed without a provider call; a controlled provider selects `catalog-search-input`, receives exactly one real Playwright retry, fills only the selected element and persists correct LLM evidence. Focused browser proof: 3/3 PASS; full unit: 92 PASS; full E2E: 5/5 PASS. Product changes: zero. Commit: `b3aae41` (`test: validate bounded LLM recovery in real browser`). | **PASS.** S2.4 behavior survived a real browser boundary without product rescue changes. | A sterile target is appropriate for proving mechanics, but it is not general product validity. More dynamic environments such as PhoenixQA Chaos App remain a later validation tier. |
| **S2.6 — first real Ollama run** | Replace only the controlled provider with the real local model while keeping the same browser target, ambiguity, shortlist and oracle. Preserve the first observation before any prompt/context tuning. | Evidence-first harness ran outside the repo on clean `main` at `b3aae41`, Ollama 0.32.9, model `qwen2.5-coder:7b`, timeout 30 s. Preflight confirmed real `AMBIGUOUS` with shortlist `global-search-input` / `catalog-search-input` and froze the provider SHA256. **Authoritative first completed run:** `20260819T152020Z`. Qwen returned `VALIDATED_SELECTION` for `catalog-search-input`; one runtime retry filled `catalog-search-input="hammer"` while `global-search-input=""`; browser oracle passed; RepairRecord persisted `repair_method=llm`, `runtime_result=recovered`, `test_result=passed`, `selected_score=null`; provider latency 21091 ms. A second unchanged confirmation run at `20260819T152104Z` produced the same correct decision and oracle with 4100 ms provider latency. No repo changes were produced by either run. | **PASS on the first completed real-model run.** No prompt or context tuning was needed to obtain the expected selection. | The first live evidence does **not** justify adding a glossary, domain hints or broader context. Prompt tuning must be triggered by evidence of a specific deficiency, not by anticipation. The repeated PASS is useful stability evidence but does not replace or rewrite the authoritative first-run result. |
| **S2.7 — evidence-driven correction if needed** | Change the smallest justified part of the contract only if S2.6 exposes a real gap. | Reviewed S2.6 first-run and confirmation evidence before changing prompt, context, heuristics or provider behavior. | **NOT REQUIRED.** S2.6 produced no correction-triggering finding. | Planned slices are conditional validation tools, not obligations to manufacture code changes. A green evidence boundary should remain unchanged until a later real failure demonstrates what is missing. |
| **S2.8 — supported framework acceptance** | Prove the bounded LLM path through the real `qa-automation-framework` integration while preserving one existing business test and all of its original assertions. | External acceptance harness ran outside both repos against TRE `42fa4b1` and framework `4d916de`. Authoritative run: `run-20260819T171427Z`; harness SHA256 `a207e7dbcdc6b222d5caa692e458440fa38ea694c4b527029e6aeb0cc31f56f9`. The same checkout test produced: TRE OFF -> locator timeout FAIL; TRE ON / LLM OFF -> deterministic bounded ambiguity, no provider call, FAIL closed; TRE ON + real `qwen2.5-coder:7b` -> `catalog-search-input`, one validated retry, unchanged full test PASS. The deterministic record contained 23 ranked action-compatible candidates, `selected_score=0.798925`, `llm_evidence.eligible=true`, `call_attempted=false`; the LLM record persisted `repair_method=llm`, `runtime_result=recovered`, `test_result=passed`, `selected_score=null`, provider outcome `validated_selection`, latency 17280 ms. No framework or TRE source was changed to obtain PASS. | **PASS.** The supported framework boundary validated the Sprint 2 one-call/one-retry contract with the unchanged original business oracle. | `candidate_count` is not shortlist size; bounded eligibility is a separate deterministic fact. Runtime pytest node IDs may include browser parameters such as `[chromium]`, so acceptance verifiers must preserve truthful parametrized identity instead of assuming an unparameterized node ID. |
| **S2.9 — closure and acceptance-basis evolution** | Close Sprint 2 without adding unproven product capability and update only documentation/requirements justified by execution evidence. | Reviewed S2.8 execution and corrected verifier evidence, then reviewed stale public architecture/testing/README descriptions. A separate CI finding was also closed operationally: a GitHub-hosted runner had stalled for over an hour during `playwright install --with-deps chromium`; commit `fa6cd6f` bounded `browser-repair` to 30 minutes and Chromium installation to 15 minutes without changing the Playwright strategy, and was merged to `main` as `dbd5510`. | **CLOSURE SLICE.** No product behavior change is authorized by S2.9. | Requirements evolve where evidence exposes a real obligation or verifier error. Documentation must distinguish supported bounded acceptance from broader robustness claims that remain deferred. |

### Sprint 2 conclusions

1. **Deterministic logic remains the authority over eligibility and execution.**
   Ollama is not a general healer. It is invoked only after deterministic logic
   identifies one bounded ambiguity, and its output still passes an exact local
   allowlist before any browser side effect.

2. **The fallback remains deliberately one-shot.**

   ```text
   deterministic ambiguity
   → at most one Ollama call
   → deterministic response validation
   → at most one browser retry
   → unchanged test continues
   ```

   There is no reflection loop, second model judge, self-correction conversation,
   model fallback chain or repeated browser repair loop in Sprint 2.

3. **Evidence semantics proved as important as selection mechanics.**
   Configuration and runtime events are separate. A RepairRecord must not imply
   model use merely because LLM mode was enabled, and a validated LLM selection
   must not imply that the browser retry or final test succeeded.

4. **Fail-closed behavior is part of the feature, not a fallback failure.**
   Timeout, transport failure, invalid JSON, schema mismatch, abstention,
   outside-allowlist selection and too-broad ambiguity all preserve the original
   failure path rather than weakening the acceptance oracle.

5. **A controlled browser target was the correct intermediate proof.**
   S2.5 isolated the runtime wiring in real Chromium without introducing target
   instability. It deliberately does not establish behavior on complex,
   dynamic or externally controlled frontends.

6. **The first real Ollama observation must remain authoritative.**
   The first completed S2.6 run already selected the expected locator and passed
   the browser oracle. The later repeated PASS is additional evidence, not a
   replacement for the first run. Future tuning must not rewrite this history.

7. **Prompt and context have different responsibilities.**
   The prompt defines decision policy; bounded context supplies facts. If a
   future run fails because the supplied facts cannot distinguish candidates,
   the first question should be whether generic evidence such as an accessible
   name or local scope is missing—not how to teach the prompt domain-specific
   locator vocabulary.

8. **There is currently no evidence-based reason to expand the prompt.**
   In particular, Sprint 2 does not justify a locator glossary or explanatory
   dictionary added only to steer Qwen toward `catalog-search-input`. Such a
   change would be premature tuning after a successful first live run.

9. **Sprint 2 is accepted through the supported framework boundary, not proven
   generally robust.**
   S2.8 validated the actual `qa-automation-framework` integration with the same
   existing checkout test and original assertions across OFF, deterministic-only
   and real-Ollama modes. This is materially stronger than the controlled TRE
   fixture, but it still does not prove arbitrary selector families, dynamic
   frontends or enterprise applications.

10. **Acceptance evidence fields must be interpreted by their real contract.**
    S2.8 exposed a verifier bug that treated `candidate_count` as shortlist size.
    The product contract actually records all ranked action-compatible candidates;
    bounded shortlist eligibility is separate. Evidence checking must validate
    the meaning of a field rather than infer a convenient meaning from its name.

11. **Runtime test identity includes framework/plugin parametrization.**
    pytest-playwright appended `[chromium]` to the node ID. Corrected verification
    accepted the truthful runtime identity while preserving the intended base
    test. This was a verifier correction, not a product repair.

12. **Infrastructure stalls need bounded failure, not product redesign.**
    A GitHub-hosted `apt`/mirror stall during Playwright dependency installation
    did not justify removing `--with-deps` or changing browser-repair behavior.
    The smallest evidence-driven response was to bound the job and installation
    step with timeouts.

### Requirements evolved by S2.8/S2.9

The Sprint 2 acceptance basis now carries these forward-looking obligations:

1. Framework acceptance for the bounded LLM slice uses the same original test and
   original assertions across TRE OFF, deterministic-only and real-Ollama modes.
2. A bounded ambiguity is proven by the deterministic selection state and LLM
   eligibility/shortlist contract. `candidate_count` must not be treated as
   shortlist length.
3. Evidence correlation must preserve real pytest node IDs, including supported
   parametrization such as `[chromium]`, while still matching the intended base
   test identity.
4. Correcting a verifier does not rewrite the historical execution. The original
   run remains immutable and corrected verification is appended.
5. Passing S2.8 proves the current supported framework integration only. Broader
   robustness claims require independent future evidence.

These obligations apply forward. They do not retroactively rewrite S2.5 or S2.6
evidence collected under the earlier basis.

---

## Sprint 3 planning lesson — optimize for engineering effectiveness, not LLM usage

**Planning date:** 2026-08-19

**Status:** Established for Sprint 3+

### Problem

After Sprint 2 proved that a bounded local LLM can resolve one real locator
ambiguity, the next risk is architectural rather than model-specific:
TestRepairEngine could drift into treating LLM usage itself as the objective.

That would turn an engineering recovery component into a model-comparison or
research project. It would also add latency, cost, data exposure and new failure
modes to cases that Playwright or deterministic logic can already solve safely.

The product objective is narrower:

> Restore the failed technical interaction with the least powerful mechanism
> that has sufficient evidence to do so safely, then let the unchanged original
> test remain the oracle.

### Decision — escalation must be earned

Future recovery design and validation follow this order:

```text
native Playwright / framework behavior
-> deterministic / heuristic TestRepairEngine recovery
-> bounded local LLM assistance
-> when local automation is insufficient:
   -> remote / online LLM when stronger machine reasoning is justified
   OR
   -> human review when domain, risk or evidence requires human authority
```

This is a preference order, not a requirement to execute every stage for every
failure.

If normal Playwright or framework behavior already handles the condition
reliably, TestRepairEngine should not add a repair layer merely to demonstrate
healing. If deterministic evidence is sufficient, an LLM should not be called
for reassurance.

Each more expensive or more powerful stage must be justified by evidence that
the preceding stage is insufficient for that class and difficulty of problem.

### Local LLM before remote LLM

The local model remains the preferred machine-assisted reasoning boundary.

A local model should not be expected to reconstruct an application from a vague
"fix this test" request. TestRepairEngine should first do the engineering work of
making the problem diagnosable:

- classify the failed interaction,
- collect bounded evidence relevant to that failure,
- provide useful structural/runtime facts and failure logs,
- remove irrelevant or sensitive payload,
- define the allowed decision space,
- explain the requested decision precisely,
- validate the result deterministically before execution.

If the local model fails, the first question is therefore not "which larger
model should replace it?" but "what evidence or problem formulation was missing?"

A remote/online LLM becomes a justified escalation only when the bounded evidence
and task formulation are already good, the local model still fails repeatedly on
a materially useful case, and the additional cost/data-transfer boundary is
acceptable.

Human review remains the final authority when evidence is contradictory,
business/domain interpretation is required, the action is too risky for automatic
execution, or no automated tier can justify a safe decision.

### Validation maturity follows realistic difficulty

Every supported healing capability should eventually be tested across increasing
levels of application difficulty rather than receiving one synthetic PASS and
being called complete.

The reusable maturity path is:

```text
controlled case
-> realistic ambiguity / dynamics
-> independently evolved target
-> unchanged business-flow oracle
```

Difficulty should represent real application problems, not artificial complexity
added only to make an LLM struggle.

Different failure/healing types may reach different maturity levels at different
times. A capability claim must therefore be limited to the strongest level that
has actually been validated.

### Consequence for Sprint 3

Sprint 3 should increase the quality of evidence before increasing the breadth of
healing functionality.

The first target is to take the already implemented Sprint 2 locator-recovery
capability into a harder, independently evolved or dynamic frontend and observe
which layer of the escalation policy is actually needed.

This planning decision does not authorize a new healing type, remote LLM
integration or automatic human-escalation workflow. Those require their own
evidence-driven slices.

---

## Sprint 3 — independent dynamic validation of existing locator recovery

**Review date:** 2026-08-22

**Status:** Closed — current `data-testid` locator recovery validated through the
frozen PhoenixQA LOW, MEDIUM and HIGH configurations; natural LLM escalation was
not required.

### Goal and frozen boundary

Sprint 3 did not start by adding another healing type. It took the existing
Sprint 2 locator-recovery capability into an independently evolved dynamic
frontend and asked which recovery tier was actually needed as difficulty
increased.

The target was the frozen PhoenixQA Chaos App at:

```text
6e28811e37d9498a4d06237e1b26bf06b6159552
```

PhoenixQA's own healer remained disabled. Large runtime evidence stayed outside
the repository under `TestRepairEngine-local-artifacts`.

The validation intentionally preserved:

- the original broken `data-testid` locators,
- deterministic scoring and ambiguity thresholds,
- the one-retry contract,
- LLM eligibility rules,
- the target implementation,
- the business outcomes used as final oracles.

Product changes were allowed only after a failure had first been preserved as
evidence and classified.

### Validation chain

| Slice | Evidence | Result | What it established |
|---|---|---|---|
| **S3.1 — stable target preflight** | `run-20260820T163217Z` | **PASS** | The frozen target and login business flow work with stable selectors before recovery is introduced. TRE was not imported and the PhoenixQA healer was not used. |
| **S3.2-A — LOW / TRE OFF** | `run-20260820T165244Z` | **PASS** | Official LOW selector rotation broke the original `username`, `password` and `btn-login` test IDs before repair. |
| **S3.2-B — LOW / TRE ON / LLM OFF, pre-fix** | `run-20260820T165756Z` | **FAIL** | Username and password recovered, but the real Playwright collector dropped the rotated login button after an editability metadata probe error. The failure became `TRE-FIND-001` / Issue #5. |
| **TRE-FIND-001 correction** | correction commit `5c8f50048f06bd2612ec89280cbad0847d5d5bda` | **FIXED** | A failed non-essential `is_editable()` probe now degrades to `editable=False` instead of discarding an otherwise valid click candidate. Scoring, thresholds, ambiguity policy and LLM policy were unchanged. |
| **S3.2-B — LOW post-fix** | `run-20260822T064419Z` | **PASS** | All three original locators failed naturally first and then recovered heuristically. The unchanged `Welcome, admin.` oracle passed with zero LLM calls. |
| **S3.3-A — MEDIUM / TRE OFF** | `run-20260822T073152Z` | **PASS** | Official MEDIUM activated `selector_rotation + dom_mutation`; the original login locators still failed before repair. |
| **S3.3-B — MEDIUM / TRE ON / LLM OFF** | authoritative `run-20260822T100403Z` | **PASS** | All three login locators recovered heuristically in the presence of MEDIUM DOM mutation and the business oracle passed with zero LLM calls. |
| **S3.4-A — HIGH / TRE OFF + timing proof** | `run-20260822T105112Z` | **PASS** | Official HIGH activated `selector_rotation + dom_mutation + async_delay`. `AddItemForm` showed a real hidden/absent confirmation phase followed by native visibility after about 972 ms, while the original locators remained broken. |
| **S3.4-B — HIGH / TRE ON / LLM OFF** | `run-20260822T125113Z` | **PASS** | Five broken locator interactions recovered heuristically. Login and Add Item business outcomes passed. The real async delay was handled by native Playwright waiting (about 1886 ms), not by TRE timing healing. LLM calls remained zero. |
| **S3.5 — natural LLM escalation** | LOW/MEDIUM/HIGH evidence | **NOT REQUIRED / NOT EARNED** | No tested interaction reached the bounded `AMBIGUOUS` state. Calling Ollama only to demonstrate model usage would have violated the escalation policy. |
| **S3.6 — additional correction after higher-level validation** | MEDIUM/HIGH evidence | **NOT REQUIRED** | After the LOW collector defect was corrected, MEDIUM and HIGH exposed no additional product defect requiring remediation. |

The earlier MEDIUM run `run-20260822T080523Z` is retained as useful behavioral
PASS evidence but is not the authoritative acceptance record because its
external helper carried stale S3.2/LOW provenance in the probe filename and
RepairRecord node ID. The corrected unchanged rerun
`run-20260822T100403Z` is authoritative for S3.3-B.

### Lessons that survive Sprint 3

1. **Failure is a first-class validation result.**
   The pre-fix LOW failure was not a bad outcome to hide. It exposed a real
   collector defect, established its boundary and justified the smallest product
   correction. The later PASS does not replace that failure; the two runs form
   one evidence chain.

   > Do not optimize validation for green results. Optimize it for discovering
   > the true boundary of each recovery tier.

2. **Escalation must be earned by the failure state.**
   LOW, MEDIUM and HIGH were all solved by deterministic locator recovery after
   the LOW collector correction. No bounded ambiguity occurred, so no LLM call
   was justified. Zero LLM calls is therefore a positive engineering result, not
   missing functionality.

3. **Native framework behavior keeps first authority.**
   HIGH exercised a real 300–2000 ms PhoenixQA asynchronous delay on
   `AddItemForm`. Playwright's native wait handled it inside the 3 s observation
   window. TRE did not manufacture a short timeout or add timing healing merely
   to claim another repaired failure type.

4. **A clean Git repository does not by itself freeze runtime behavior.**
   Early Sprint 3 work showed that an ignored local PhoenixQA `.env` could change
   the Chaos App runtime while the repository SHA and worktree still looked
   correct. Authoritative runs therefore used `git archive` snapshots of the
   exact frozen PhoenixQA commit and excluded the ignored local `.env`.

   ```text
   source revision frozen
   !=
   runtime configuration frozen
   ```

5. **Test doubles must model relevant integration failure semantics.**
   The unit-test `FakeElement` returned a boolean from `is_editable()`, while the
   real Playwright boundary could raise `PlaywrightError` for an otherwise useful
   click candidate. Independent browser validation exposed a defect that happy
   path mocks could not reveal.

6. **Failure of optional metadata should degrade that metadata, not destroy
   stronger evidence.**
   For a click target, inability to establish editability is not enough reason to
   discard a visible, enabled, click-compatible button. `TRE-FIND-001` established
   the reusable collector rule:

   ```text
   optional metadata probe fails
   -> mark that metadata unavailable / conservative
   -> preserve otherwise valid candidate evidence
   ```

7. **Configured or declared mechanisms are weaker evidence than exercised
   behavior.**
   Merely running PhoenixQA with `HIGH` would not have proven timing noise on the
   login flow because `async_delay` is exercised by `AddItemForm`, not by
   `LoginForm`. S3.4 therefore added a real Add Item path and observed the delayed
   confirmation instead of treating the status panel as sufficient proof.

8. **Behavioral PASS and authoritative evidence are different facts.**
   The first MEDIUM recovery run behaved correctly but carried stale harness
   provenance. It remained useful diagnostic evidence, while a clean rerun with
   truthful S3.3 identity became the authoritative record. Evidence identity is
   part of acceptance quality.

9. **Capability claims must describe what TRE actually repaired.**
   MEDIUM and HIGH do not prove generic DOM-mutation healing or timing healing.
   They prove that the current `data-testid` locator-recovery capability remained
   effective while the tested flows ran in the presence of those target dynamics,
   and that native Playwright waiting was sufficient for the observed async delay.

10. **Independent dynamic validation is materially stronger than a controlled
    fixture, but it is still bounded evidence.**
    Sprint 3 moved current `data-testid` recovery from a controlled/framework
    proof into the frozen independently evolved PhoenixQA target across three
    difficulty levels. It still does not establish arbitrary locator families,
    arbitrary DOM rewrites, actionability recovery or enterprise-wide robustness.

### Sprint 3 conclusion

The current validated escalation outcome is:

```text
LOW
-> deterministic locator recovery sufficient after one real collector defect was fixed
-> LLM 0

MEDIUM
-> deterministic locator recovery sufficient in the presence of DOM mutation
-> LLM 0

HIGH
-> deterministic locator recovery sufficient for five broken locators
-> native Playwright waiting sufficient for the exercised async delay
-> LLM 0
```

Sprint 3 therefore strengthens the evidence for the existing narrow capability
without expanding product authority. Future healing breadth should still be
triggered by a real failure that the current lower tiers cannot solve safely.
---

## Sprint 5.1 - prove process identity directly before claiming process-safe correlation

**Review date:** 2026-08-24

**Status:** Validated for one bounded two-worker `pytest-xdist` scenario; no
product correction required.

### Problem

The roadmap identified pytest-xdist/process-safe correlation as an unproven
runtime boundary.

The implementation already used process-local runtime state and collision-safe
RepairRecord publication, but architecture alone could not establish that
parallel pytest workers would preserve:

- the correct pytest node association,
- independent pending-repair state,
- independent failed-test state,
- final `runtime_result` / `test_result` correlation,
- collision-free persistence into one shared output directory.

The qualification therefore started with no product change.

### Pre-run lesson - interpreter identity is evidence

An initial environment check exposed a harness problem before an immutable
qualification run was created.

The shell resolved `python` to a user-installed Python 3.12 environment rather
than the repository `.venv`. `pytest-xdist` installed into user site-packages and
the TestRepairEngine pytest plugin was then unavailable.

This was not a TestRepairEngine result. The qualification was stopped and the
environment boundary was corrected first.

The durable lesson is:

```text
"virtual environment expected"
!=
"interpreter identity proved"
```

Qualification tooling that depends on an environment must verify the actual
`sys.executable` before collecting evidence.

### Attempt 1 - useful behavior, invalid process oracle

The first immutable run was:

```text
run-20260824T162324Z
```

The behavioral path looked healthy:

- two RepairRecords were persisted,
- both repairs were `runtime_result=recovered`,
- one original test finalized as `passed`,
- one deliberately failed after recovery and finalized as `failed`,
- repair IDs were distinct,
- no LLM call occurred,
- the normal repository regression remained green.

However, the harness tried to infer process isolation from assumptions that had
not been proved: scheduler placement, TRE `run_id` semantics and incidental
pytest node-ID formatting.

The run therefore remained **INCONCLUSIVE** rather than being reinterpreted as a
product failure.

### Attempt 2 - process identity proved directly

The authoritative rerun was:

```text
run-20260824T163032Z
```

The corrected harness made worker/process identity an explicit observation:

- `PYTEST_XDIST_WORKER` identified `gw0` and `gw1`,
- worker markers recorded OS process IDs `3168` and `16708`,
- both markers carried xdist test-run UID
  `d3c41dfd4af84d649a4e04e3905a178f`,
- the PASS repair was explicitly executed only on `gw0`,
- the FAIL-after-repair scenario was explicitly executed only on `gw1`.

This established two different worker processes inside the same distributed
pytest run before evaluating TRE correlation.

The resulting RepairRecords remained independent:

```text
gw0
-> search-input -> catalog-search-input
-> runtime_result=recovered
-> test_result=passed

gw1
-> account-name -> account_name
-> runtime_result=recovered
-> test_result=failed
```

The records had distinct repair IDs and distinct process-local TRE run IDs while
sharing the same RepairRecord output directory. No collision or cross-test final
result leakage occurred.

### Decisions and lessons

1. **Process identity must be observed directly when it is part of the oracle.**
   Do not infer it from scheduler expectations, `run_id` semantics or incidental
   node-ID formatting when worker ID and PID can be recorded directly.

2. **A harness defect does not justify a product finding.**
   Attempt 1 exposed an invalid acceptance assumption. Product code remained
   frozen while the oracle was corrected. No `TRE-FIND-003` was opened.

3. **Runtime recovery and original-test success remain separate across the tested
   process boundary.**
   Both worker repairs succeeded, while their unchanged pytest outcomes diverged
   exactly as intended: one `passed`, one `failed`.

4. **Shared persistence survived the tested two-process case.**
   Two workers wrote independent UUID-named RepairRecords into one output
   directory without destructive overwrite or collision.

5. **A bounded PASS must stay bounded.**
   S5.1 does not establish unrestricted xdist or concurrency support. It does not
   cover high worker counts, sustained write pressure, worker restart/crash,
   distributed/network filesystems, xdist plus Ollama, or framework/external
   xdist acceptance.

6. **Qualification tooling is not automatically a product dependency.**
   `pytest-xdist` was installed locally to test the boundary. It should enter
   `pyproject.toml` only if xdist support becomes an intentionally supported and
   continuously regression-tested product property.

### Consequence

S5.1 closes without a product change.

The validated claim is deliberately narrow:

> In the tested two-worker pytest-xdist scenario, TestRepairEngine preserved
> independent runtime-repair evidence and correct final pytest correlation across
> two proven worker processes sharing one RepairRecord output directory.

Future concurrency work should begin from a new evidence gap rather than
expanding the claim from this single bounded qualification.
