# SPEC-HARNESSBENCH-V2 — Harness-Neutral Agent Systems Evaluation

**Status:** PARKED / POST-v1 DESIGN
**Program:** RESIDUAL v2
**Roadmap branch:** `v2/solpi-evidence-context-environment-bank`
**Implementation authority:** none until the v2 kickoff gate in `docs/v2/ROADMAP.md` is satisfied.
**Primary question:** Given the same frozen task, model, repository state, tool surface, environment, budgets, and acceptance contract, what changes when the agent harness changes?

## 1. Motivation

Agent-system outcomes are jointly produced by the model, harness, tools, environment, memory/context policy, communications topology, verifier, and human interventions. Comparing models while allowing harness behavior to drift confounds those effects. Comparing harnesses without freezing model/runtime and task state has the same problem.

HarnessBench makes the harness a first-class experimental variable while RESIDUAL remains the authority-constrained experiment controller, evidence plane, and verifier coordinator.

The objective is not a universal leaderboard. The objective is reconstructable evidence about causal contributors to reliable agentic engineering under explicitly bounded conditions.

## 2. Scope and non-claims

HarnessBench MAY execute, observe, normalize, replay, compare, generate candidates/reports, and request escalation.

HarnessBench MUST NOT gain authority to merge code, modify protected branches, weaken qualification policy, rewrite raw evidence, override verifier outcomes, silently increase budgets, silently alter tasks, or convert an invalid/unknown result into PASS.

A HarnessBench result is evidence about the named task corpus, revisions, runtime, configuration, and protocol. It is not proof that a harness or model is universally superior.

## 3. Experimental invariants

For a controlled harness comparison, the following MUST be frozen or content-addressed before outcome access:

- task and acceptance contract;
- repository commit/tree and fixture state;
- environment image/manifest and host capability class;
- model identity, model artifact/digest where available, inference engine, reasoning level and decoding controls;
- context limit and initial context;
- allowed/forbidden tools and network policy;
- credentials capability set without exposing secret values;
- time, token, model-call and tool-call budgets;
- verifier implementation/configuration;
- memory policy;
- randomization seed and run order policy;
- harness identity/version/configuration, which is the intended treatment variable.

If a non-treatment invariant drifts, the run is INVALIDATED or separated into a different experimental cell. It is never silently pooled.

## 4. Core objects

### 4.1 HarnessExperiment

A canonical manifest identifies protocol revision, corpus/task, repository/environment identities, model/runtime identity, harness adapter/configuration, budgets, verifier, randomization, authority boundary, and expected evidence roots.

### 4.2 FrozenMission

Every harness receives a semantically equivalent immutable mission envelope containing objective, starting state, tool contract, acceptance contract, resource budgets, network policy, human-intervention policy, and evidence obligations.

The canonical mission bytes are hashed before launch. Post-launch mutation invalidates the run.

### 4.3 HarnessAdapter

Harness-specific behavior is isolated behind a narrow contract:

```python
class HarnessAdapter(Protocol):
    def identify(self) -> HarnessIdentity: ...
    def capabilities(self) -> HarnessCapabilities: ...
    def configure(self, config: HarnessConfig) -> None: ...
    def start(self, mission: FrozenMission) -> RunHandle: ...
    def events(self, run: RunHandle) -> Iterator[HarnessEvent]: ...
    def interrupt(self, run: RunHandle) -> None: ...
    def terminate(self, run: RunHandle) -> None: ...
    def collect(self, run: RunHandle) -> HarnessArtifactBundle: ...
```

Initial targets: `generic_cli`, `codex`, `openclaw`, `residual_native`, and `replay`. Additional adapters must not require changes to the experiment authority model.

### 4.4 HarnessBenchReceipt

Every terminal run emits a receipt or an explicit receipt-generation failure. The receipt binds experiment/protocol ID, task/repo/environment/model/harness identities, budgets, seed, timestamps, termination reason, raw and normalized trace roots, artifact/verifier roots, metric vector, human interventions, contamination state, and receipt digest.

No valid receipt means no admissible benchmark result.

## 5. Evidence architecture

Raw harness-native evidence is immutable and authoritative for what the harness emitted. Normalized traces are rebuildable projections.

```text
harness-native evidence
        |
        v
content-addressed immutable evidence store
        |
        +--> normalization projection
        |        |
        |        v
        |   HarnessBench analytics
        |
        +--> replay / independent inspection
```

Normalization MUST NOT replace, truncate, or rewrite the raw evidence root.

Canonical normalized events include RUN_STARTED, MODEL_CALL_STARTED/COMPLETED, TOOL_REQUESTED/COMPLETED, FILE_READ, FILE_MUTATED, COMMAND_EXECUTED, TEST_EXECUTED, RETRY, SELF_CORRECTION, ESCALATION, HUMAN_INTERVENTION, BUDGET_WARNING/EXHAUSTED, CANDIDATE_SUBMITTED, VERIFICATION_STARTED/COMPLETED, RUN_TERMINATED, and CONTAMINATION_DETECTED.

Unknown harness-native events remain retained even when no normalized mapping exists.

## 6. Isolation and contamination

Each trial receives an isolated git worktree or equivalent immutable-base overlay, process/runtime boundary, artifact directory, environment namespace, credential capability scope, and bounded network policy.

State may cross trials only through an explicitly declared RESIDUAL channel.

Contamination detectors cover:
- cross-run filesystem/state leakage;
- shared conversation history or undeclared memory;
- cached solution leakage;
- repository/test fixture mutation;
- hidden test exposure;
- environment, model, runtime, or harness drift;
- shared communications not declared in the experimental cell.

Contamination produces `INVALIDATED`, distinct from `FAIL`. Evidence is retained.

## 7. Metrics

HarnessBench reports a metric vector, never a single universal score.

Primary outcomes:
- independently verified task success;
- false-completion rate (harness claims completion, verifier rejects);
- time to verified completion;
- model calls/tokens;
- tool calls and failed tool calls;
- retries/self-corrections;
- regressions introduced;
- verifier failures;
- human interventions;
- budget exhaustion;
- recovery success;
- evidence completeness;
- deterministic replay divergence.

Derived metrics may include Verified Work / Token, Verified Work / Wall Time, Useful Work / Model Call, Recovery Efficiency, Human Intervention Rate, and Epistemic Correction Rate. Every derived metric must declare its formula and denominator handling.

Comparisons SHOULD expose distributions and Pareto frontiers (reliability, latency, compute/cost, intervention burden) rather than collapsing tradeoffs into an overall winner.

## 8. Experimental design

Single runs do not establish comparative claims. Campaigns support paired tasks, randomized execution order, repeated trials, preregistered exclusions, confidence intervals, effect sizes, and bootstrap/permutation methods where appropriate.

Minimum confirmatory campaign parameters are protocol-defined rather than hard-coded. Exploratory results must be labeled exploratory.

Factorial dimensions may include:
`model × harness × reasoning effort × context × task class × tool policy × memory policy × communications topology × concurrency × host class`.

A change in more than one intended factor creates a multi-factor experiment and must be analyzed as such.

## 9. Local inference and hardware manifests

Local model experiments bind the host and inference path into the environment identity. A host manifest SHOULD record CPU, RAM, GPU/VRAM, driver/runtime versions, inference engine, model artifact/digest, offload policy, context size, and available telemetry.

This allows controlled campaigns such as a 64-GB host with an RTX 4070 running `gpt-oss:20b`, while preventing those results from being generalized to unrelated hardware/runtime profiles.

Telemetry may include GPU utilization/VRAM, CPU utilization, system memory, tokens/sec, model latency, energy where available, and resource-pressure events. Telemetry is observational unless explicitly made part of acceptance.

## 10. Swarm and heterogeneous-harness extension

HarnessBench progresses from:
1. single agent / single harness;
2. multi-agent / homogeneous harness;
3. distributed homogeneous harness;
4. multi-agent / heterogeneous harness;
5. distributed heterogeneous harness.

For heterogeneous experiments, every worker identity binds role, harness, model/runtime, host, communication permissions, and budget. Shared communication MUST traverse an explicit RESIDUAL-controlled channel and be represented in the evidence graph.

This creates a direct research bridge to shared communications / SC-MESH: RESIDUAL can test whether outcomes change because of harness choice, topology, communications semantics, or their interaction.

## 11. Environment Bank integration

ENVB-002 supplies immutable benchmark environments and generation/split discipline. HarnessBench consumes Environment Bank generations but cannot mutate them during a campaign.

Required split roles:
- development/screening;
- validation;
- held-out confirmatory.

Outcome access to held-out environments before preregistration invalidates confirmatory status.

First-failure evidence from v1 may seed replay environments, but provenance must identify that those cases originated during v1 development and may therefore be familiar to systems trained or prompted from project history.

## 12. AX-21 and M6 integration

HarnessBench is an instrument for AX-21-style research, not a replacement for its preregistration/evidence discipline.

M6 improvement proposals may use HarnessBench screening to ask whether an observed improvement is model-, harness-, topology-, or control-layer-sensitive. Protected changes still require the existing human gate and qualification path.

HarnessBench itself cannot use benchmark outcomes to autonomously rewrite its protocol, acceptance criteria, or protected implementation.

## 13. Replay bundle

Each run produces a content-addressed bundle conceptually containing:

```text
HB-<experiment>/<run>/
  experiment.json
  mission.json
  environment.json
  model.json
  harness.json
  raw/
  normalized/
  artifacts/
  verifier/
  telemetry/
  receipts/
  manifest.sha256
```

A third party should be able to inspect identities, recompute hashes, rebuild normalized projections, rerun deterministic verifiers where applicable, and determine why the run received PASS/FAIL/INVALIDATED/UNKNOWN without trusting the dashboard.

## 14. Terminal states

- `PASS`: acceptance contract independently verified and evidence obligations satisfied.
- `FAIL`: admissible run completed but acceptance contract failed.
- `INVALIDATED`: experimental invariants or contamination controls were violated.
- `UNKNOWN`: evidence is insufficient to classify PASS/FAIL safely.
- `ABORTED`: authorized interruption before admissible completion.

Harness-native "success" is an observation, not a RESIDUAL PASS.

## 15. Adversarial qualification

Before comparative claims are enabled, inject at least:

HB-Q01 false completion; HB-Q02 parent exit with child alive; HB-Q03 out-of-worktree mutation; HB-Q04 model/runtime drift; HB-Q05 harness-config drift; HB-Q06 dropped event; HB-Q07 duplicate event; HB-Q08 event reordering; HB-Q09 budget overrun; HB-Q10 network-policy escape attempt; HB-Q11 cached-solution contamination; HB-Q12 shared-memory contamination; HB-Q13 verifier crash; HB-Q14 RESIDUAL crash/restart; HB-Q15 host loss; HB-Q16 success claim with failing acceptance tests; HB-Q17 undeclared cross-agent communication; HB-Q18 normalized-trace corruption while raw evidence remains intact.

Every case requires expected state transition, retained first-failure evidence, and a mutation/sensitivity control proving the detector is live.

## 16. Implementation work packages

- **HB-00** schema + canonical serialization.
- **HB-01** FrozenMission + immutable identity.
- **HB-02** HarnessAdapter API/capability negotiation.
- **HB-03** generic CLI adapter.
- **HB-04** Codex adapter.
- **HB-05** OpenClaw adapter.
- **HB-06** normalized trace projection + rebuild.
- **HB-07** verifier integration + terminal-state authority.
- **HB-08** HarnessBenchReceipt.
- **HB-09** replay bundle/export.
- **HB-10** contamination/drift detection.
- **HB-11** campaign scheduler/randomization.
- **HB-12** statistics + Pareto reporting.
- **HB-13** distributed/swarm campaigns.
- **HB-14** heterogeneous harness/model campaigns.
- **HB-15** local hardware/runtime telemetry.
- **HB-16** held-out Environment Bank integration.
- **HB-17** adversarial qualification campaign.

## 17. Dependency graph

```text
EVPR-001 ───────────────┐
OBSH-003 / CMPE-004 ───┼─> evidence/context identity
ENVB-002 ───────────────┼─> frozen environments / held-out splits
SC-MESH ────────────────┼─> declared shared communications
                       v
HB-00..10 -> HB-11/12 -> HB-13/14/16 -> HB-17
                       |
                       v
                 M6 / AX-21 studies
```

HB-00 through HB-12 can progress without heterogeneous swarm support. HB-13/HB-14 require the relevant communications/control-plane interfaces to be qualified.

## 18. Completion claim

RESIDUAL v2 MUST NOT claim harness-comparison capability until at least two independently implemented harness adapters execute the same frozen corpus against the same frozen model/runtime and repository/environment states; complete independently inspectable evidence is retained for every admissible trial; false completion and deliberate contamination injections are correctly classified; repeated trials use preregistered campaign rules; normalized projections are rebuildable from raw evidence; and comparative results can be reconstructed from sealed experiment artifacts without trusting the UI.

A stronger heterogeneous-swarm claim requires separate qualification of distributed communications, host loss/rejoin, role identity, and cross-harness evidence continuity.

## 19. Open research questions

- How much variance in verified completion is attributable to model versus harness versus environment?
- Which harness policies improve reliability at the cost of latency or compute?
- Do richer self-correction loops reduce false completion or merely increase token spend?
- When does context/memory policy dominate harness choice?
- Do heterogeneous harness swarms provide complementary failure modes or simply more coordination overhead?
- Can shared communications improve recovery without creating contamination or stale-state amplification?
- Which harness behaviors predict verifier rejection before terminal completion?
- How stable are harness effects across model families and hardware classes?

These questions are hypotheses to test, not claims encoded by the specification.
