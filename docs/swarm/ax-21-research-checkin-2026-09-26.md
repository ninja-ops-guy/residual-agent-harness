# AX-21 / RESIDUAL Research Check-in — 2026-09-26

**Status:** OBSERVED / NOT FROZEN  
**Accepted main observed:** `d796f36b75e730a0bab71bdba564206174393719`  
**Purpose:** append-only research maintenance record. This file does not rewrite AX-21-BASELINE-R0 or promote draft/release evidence into accepted claims.

## Material findings

### 1. P3.3 separated requested transport from observed transport

The current AX-21 research record on PR #460 preserves an important historical correction.

The original P3.3 A→B→C sequence requested gateway execution, but the required CLI device scope was denied and execution silently occurred through the embedded path. The original result therefore remains:

`PASS_WITH_TRANSPORT_LIMITATION`

with selection authority, hot reload, reversibility, semantic restore, production-session stickiness and failover classification observed, but gateway transport binding NOT_PROVEN for the original run.

A later bounded mini-experiment resolved the CLI scope through explicit device approval and retained, per turn:

- requested transport;
- observed transport;
- fallback source;
- gateway process identity;
- session identity;
- provider/model;
- configuration generation;
- gateway journal marker.

All A/B/C turns in that mini-experiment were attributed to systemd gateway MainPID `25567` with unique journal markers.

Observed sequence:

```
A: kimi/kimi-for-coding
→ mutate default binding
B: moonshot/kimi-k2.6 selected; existing billing cooldown caused skip/fallback to ollama/qwen2.5-coder:7b
→ restore
C: kimi/kimi-for-coding
```

The later mini-experiment supports gateway transport binding for its own exact scope. It does not retroactively turn the original embedded-path observation into gateway evidence.

**Falsified assumption:** requesting a transport is sufficient evidence that the requested transport executed.

**Candidate RES-UP — TRANSPORT-PROVENANCE-001:** authority-bearing execution receipts should independently bind requested transport, observed transport, gateway/process identity, session identity, configuration generation and fallback source.

### 2. Real provider loss preserved reasoning continuity but not full capability equivalence

PR #460 also records `SC-FALLBACK-001-WRENCH` on DELL7320 / Wrench, systemd gateway MainPID `25567`, during the 2026-09-25 22:36–22:58 ET window.

The Kimi endpoint was temporarily changed to dead loopback `127.0.0.1:1`, producing a bounded connection-refused/fetch failure while the gateway remained alive. The configured path then selected:

```
kimi/kimi-for-coding
→ ollama/qwen2.5-coder:7b
```

The primary endpoint was later byte-restored, and a fresh session again selected Kimi.

The retained three-stage workload continued on one session:

```
Stage 1 — Kimi
41 × 2 = 82
checkpoint persisted

provider loss

Stage 2 — Ollama qwen2.5-coder:7b
82 + 7 = 89
Stage 1 not repeated

Stage 3 — Ollama qwen2.5-coder:7b
89 × 3 = 267
Stage 2 not restarted
```

The reconciliation turn reported each stage exactly once, and the receipt reports one assistant payload per qualification turn with no stale Ollama binding after restoration.

This is meaningful live provider-loss evidence for the tested Wrench seat and workload.

It does **not** establish transparent provider equivalence. The same receipt preserves W-1:

- local qwen2.5-coder:7b kept reasoning/session continuity;
- tool calls appeared as raw JSON text;
- a stage-2 write did not persist.

Therefore the supported claim is bounded:

> the tested local fallback preserved seat liveness and reasoning/session continuity across the induced primary loss.

Unsupported claims include:

- full tool-capability equivalence;
- fleet-wide fallback equivalence;
- exactly-once side-effect execution;
- universal provider recovery.

Additional preserved observations:

- W-2: connection-refused surfaced as `fetch failed` and was classified as failover-worthy timeout;
- W-3: clearing primary-recovery state appeared turn-driven rather than an observed idle background probe;
- W-4: CLI↔gateway scope negotiation must be pre-approved for unattended automation, and embedded execution must be detectable rather than silently accepted.

**Falsified assumption:** successful fallback text generation implies transparent capability substitution.

**Candidate RES-UP — FALLBACK-CAPABILITY-VECTOR-001:** bind fallback admission and receipts to explicit capabilities such as reasoning, tool invocation, persistent side effects, structured output and execution authority. Distinguish `ALIVE_AND_EQUIVALENT` from `ALIVE_BUT_DEGRADED`.

### 3. OpenClaw dogfood produced an evidence-gated stopping condition

Draft PR #471 captures live OpenClaw Swarm Onboarding R0.1 dogfood.

Observed trajectory:

- OC-101 / Prepare Anvil reached `INTEGRATED`;
- OC-102 / Prepare ForgeV2 remained `REPAIR_REQUIRED` after multiple attempts;
- OC-103 / Prepare Gateway remained `REPAIR_REQUIRED` after multiple attempts;
- later OC-102/OC-103 mechanical checks passed while semantic reviews continued to reject the candidates because required real-world evidence was absent;
- Run Control opened with 15 passes, 200,000 tokens and a 3,600-second budget;
- it escalated after one pass with `no_runnable_tasks`, dispatch brake tripped, zero run-control tokens and about 20 ms elapsed;
- deterministic verification recorded acceptance PASS, integration FAIL with `integration_incomplete`, and review SKIPPED due to `prior_check_failed`;
- a runner operation can complete while the authoritative task remains `REPAIR_REQUIRED`;
- optional cloud assessment can fail/rate-limit after authoritative batch evidence has already been recorded.

This is a useful negative result. Additional inference did not manufacture the missing external observations, backup receipts, identity proof or human authorization.

**Falsified assumption:** every `REPAIR_REQUIRED` state is meaningfully addressable by another model/code attempt.

**Candidate hypothesis — H5 Evidence-gated stopping efficiency:** when a blocker requires external evidence or human authority, deterministic classification and retry suppression can reduce wasted model calls/tokens without reducing eventual accepted task completion.

AX-21 does not yet establish H5. The dogfood provides an observed stopping case and a candidate controlled comparison.

**Candidate RES-UP — EVIDENCE-REQUEST-001:** derive a deterministic evidence-request artifact from the exact task/review/event state, export it to a human or external collector, and admit returned evidence as a separately authenticated append-only event before deterministic re-evaluation.

### 4. Operation completion and task-state advancement are different claims

The dogfood exposed a concrete operator-facing ambiguity:

`run-OC-102 completed`

can describe completion of the attempt while OC-102 remains `REPAIR_REQUIRED`.

For research and operations, receipts should separately report:

- operation/attempt completion;
- mechanical check outcome;
- semantic review outcome;
- integration outcome;
- authoritative task-state transition.

**Candidate RES-UP — OUTCOME-LAYERING-001:** require operator messages and exported receipts to identify which lifecycle layer completed instead of using generic success language.

### 5. Evidence validators remain part of the experimental trusted computing base

PR #461 reproduced four bounded defects in the proposed v1 recovery-evidence validator:

- REC-JSON-01: NaN could bypass RPO/RTO comparisons; Infinity/nonstandard constants and overflowing exponents were admitted;
- REC-JSON-02: duplicate JSON members silently used the last value, allowing earlier contradictory evidence to disappear;
- REC-NUM-03: float coercion could erase a one-unit breach at `2**53 + 1` versus `2**53`; very large integers produced untyped overflow;
- REC-INPUT-04: invalid UTF-8 and non-object direct API input did not produce the documented typed failure.

Retained negative/repair evidence:

- original ten tests: 10 PASS;
- adversarial suite on predecessor: 23 methods, 31 failed assertions/subtests and 6 errors;
- repaired source with unchanged original/adversarial test bytes: 33 methods PASS, zero skips;
- an initial 20-second outer-tool timeout is retained; the same bounded negative suite later completed under a longer outer allowance without changing the oracle.

Current exact PR #461 head `d4027aa261bc3a4e2fa029479498850e7a9a5564` has seven named technical workflows PASS. Maintainer approval remains unsatisfied, PR-Agent advisory review is red, and no human review was recorded at the terminal observation. The proposal is review-ready but unmerged.

This is evidence about a proposed validator boundary, not evidence that a production recovery exercise passed.

**Falsified assumption:** ordinary JSON decoding plus floating-point comparison is a sufficiently strict evidence boundary for authority-bearing recovery claims.

**Candidate RES-UP — STRICT-EVIDENCE-PARSER-001:** authority-bearing evidence formats should reject duplicate keys, nonstandard constants, non-finite values, malformed roots and precision-losing coercions before semantic qualification.

### 6. Evidence-gated dogfood and fallback findings strengthen the original AX-21 baseline without replacing it

Relative to the pre-release AX-21 baseline:

- **Evidence over consensus** is strengthened: correct output/provider claims are insufficient without transport/process/session provenance.
- **Diagnostic quality constrains autonomy** is strengthened: fallback may preserve reasoning while tool/persistence capability degrades.
- **Presence/telemetry/evidence are distinct** is strengthened: a runner operation can complete while authoritative task/review/integration state remains blocked.
- **Human coordination as hidden infrastructure** remains supported: external observations and protected approvals still require explicit human/external actors.
- **H4 hierarchical inference efficiency** remains open: local fallback feasibility improved, but verified task success must be measured by capability class rather than text continuity alone.

The new observations do not establish whole-system security, autonomous recursive development or fleet-wide provider equivalence.

### 7. A convergence freeze has been proposed as an empirical control

Draft PR #473 converts the current dogfood/AX-21 lessons into an explicit v1 evidence/convergence discipline.

Its proposed machine-readable holds include:

- Ghost P3.3: do not disturb except the current bounded protocol;
- Shared Comms widening: Anvil canary only;
- dogfood E0: do not rerun without new admitted evidence;
- physical F6: wait for an accepted product head and requalified helper;
- new v1 features: blocked by default unless a defined admission reason applies.

The human-readable policy also requires:

- first failures and superseded evidence remain append-only;
- configuration, normalized/derived state, session binding, runtime registry and observed execution are separate layers;
- inference cannot substitute for missing external evidence;
- coordinator, Orchestrator, Station, worker, verifier and human authority remain separated;
- fleet widening is staged;
- bounded checkpoints are used after context overflow;
- a successful direct component call does not prove automatic routing/fallback/integration.

Exact head `bfa6d4db35e8a8237f88be80fc1794e5c86f1ca9` has the normal technical workflows green. Maintainer approval and advisory-review gates remain red. This is governance/specification evidence only; it does not freeze AX-21 or authorize release by itself.

### 8. Research-program implications

The combined observations suggest three high-value controlled experiments.

#### EXP-AX21-TRANSPORT-01 — requested vs observed execution path

Compare identical bounded tasks under:

A. gateway transport with required scope present;  
B. gateway requested but scope denied with embedded fallback possible;  
C. embedded transport explicitly requested.

Measure output correctness, requested/observed transport agreement, receipt completeness, operator detection rate and false attribution.

#### EXP-AX21-DEGRADED-FALLBACK-01 — capability-aware continuity

For a fixed checkpointed task suite, induce primary loss and compare fallback models/providers.

Measure independently:

- reasoning continuity;
- structured-output validity;
- tool invocation success;
- persistent side-effect success;
- replay/duplicate rate;
- recovery to primary;
- verified task completion;
- latency/cost.

Do not collapse these into a single UP/DOWN metric.

#### EXP-AX21-EVIDENCE-HOLD-01 — retry versus evidence-gated stopping

For blockers preregistered as requiring external evidence, compare:

A. naive bounded model retries;  
B. deterministic evidence-gated stop + exported evidence request.

Measure:

- model calls/tokens;
- wall-clock active compute;
- number of unchanged attempts;
- human actions;
- time to admissible evidence;
- eventual verified completion;
- false stop rate.

The current dogfood is an observation motivating the experiment, not the experiment itself.

## Operator interventions observed

- explicit CLI device approval was required before the gateway-mediated P3.3 repeat;
- the Wrench provider-loss experiment deliberately changed the Kimi endpoint to dead loopback and byte-restored it afterward;
- external evidence/human authorization remained required for dogfood blockers;
- no human review/maintainer acceptance has converted PR #461 or PR #473 into accepted release evidence.

These interventions should remain counted in future autonomy measurements.

## Current control conditions

### P5 operator-friction

PR #349 remains open/draft at head `625e1ce97919098dbe9d586ffcaf4b2a94257184`.

No valid post-#349 replay of the frozen question has been established in this check-in. Therefore the pre-intervention baseline remains the comparison point:

- Station direct answer: no;
- approximately 11 cold individual-agent queries;
- human synthesis required;
- external coordination state required;
- 15+ reports/session synthesized during normal operation.

Do not claim coordination-friction reduction yet.

### Release boundary

Accepted `main` remains:

`d796f36b75e730a0bab71bdba564206174393719`

GitHub currently exposes no formal repository release.

Therefore:

- no release-tag experimental cutover exists;
- AX-21-BASELINE-R0 remains a candidate pre-release baseline;
- release-tagged three-host reproduction is still required before final freeze.

## Candidate RES-UP / ImprovementSpec queue

- `RES-UP-TRANSPORT-PROVENANCE-001` — requested/observed execution-path binding.
- `RES-UP-FALLBACK-CAPABILITY-VECTOR-001` — capability-aware degraded fallback receipts/admission.
- `RES-UP-EVIDENCE-REQUEST-001` — deterministic export/admission loop for external evidence.
- `RES-UP-OUTCOME-LAYERING-001` — separate operation, check, review, integration and task-state outcomes.
- `RES-UP-STRICT-EVIDENCE-PARSER-001` — canonical strict parsing for authority-bearing evidence.
- `EXP-AX21-TRANSPORT-01` — transport-provenance controlled experiment.
- `EXP-AX21-DEGRADED-FALLBACK-01` — capability-aware fallback experiment.
- `EXP-AX21-EVIDENCE-HOLD-01` — evidence-gated stopping versus naive retry.

These are candidates, not accepted requirements.

## Paper-safe conclusions

Supported by the current evidence:

- requested execution path and observed execution path are separate experimental variables;
- local fallback can preserve reasoning/session continuity while degrading tool/persistence capabilities;
- successful text generation is not evidence of full execution equivalence;
- external-evidence blockers can produce a legitimate zero-token/no-runnable-work stopping condition;
- operation completion is not equivalent to authoritative task success;
- evidence parsers/validators themselves require adversarial qualification;
- preserving superseded and negative observations materially improves the credibility of the longitudinal record.

Not supported:

- RESIDUAL is secure in general;
- local fallback is a transparent primary replacement;
- provider recovery is fleet-wide;
- P5 operator-friction has improved;
- physical F6 has passed;
- AX-21 demonstrates sustained autonomous recursive development;
- AX-21-BASELINE-R0 is finally release-frozen.

## Next highest-value evidence

1. preserve the exact P3.3 gateway mini-experiment and SC-FALLBACK receipts/digests in the immutable Phase-3 evidence bundle;
2. run the capability-aware fallback experiment on at least one additional seat/model while retaining tool/persistence failures separately;
3. implement or prototype the deterministic evidence-request export/admission path and replay the same dogfood blocker without changing its evidence;
4. run the frozen P5 question only after #349 is genuinely integrated/qualified and record the before/after operator-friction delta;
5. keep the convergence freeze in force unless a proposed v1 change has an explicit admission reason;
6. perform the release-tagged three-host reproduction before final AX-21 baseline freeze.

**Disposition: MATERIAL UPDATE — PRESERVE.**
