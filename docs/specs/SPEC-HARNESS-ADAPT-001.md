# SPEC-HARNESS-ADAPT-001 — Model-, Task-, and Budget-Adaptive Harness Policy

**Status:** Proposed
**Research basis:** arXiv:2609.20804
**Relationship:** complements M6/M6.2 recursive-improvement work

## 1. Purpose

RESIDUAL SHOULD treat harness configuration as an experimentally optimizable surface.

Harness optimization MUST remain separate from worker authority. A different planning, context, or action policy MUST NOT enlarge filesystem, network, process, integration, receipt, approval, or merge authority.

## 2. HarnessProfile

A HarnessProfile MUST bind:
- profile ID and revision;
- model and provider identity;
- task-class identity;
- context-window budget;
- planning policy;
- context-management policy;
- action-interface policy;
- diagnostic policy;
- stagnation policy;
- verifier/evaluator revisions;
- authority-envelope hash;
- qualification-evidence hash.

Changing HarnessProfile MUST NOT enlarge the WorkerContract.

## 3. PlanningPolicy

Planning MUST be explicit, not assumed.

Supported candidate modes SHOULD include:
- none;
- continuation_scaffold;
- persistent_plan;
- stopping_scaffold.

Continuation scaffolding targets premature termination before meaningful action. Stopping scaffolding targets redundant work after an acceptable edit.

A policy MUST NOT be selected solely from model size or reputation.

## 4. ContextManagementPolicy

Context management MUST preserve:
- control/system preamble;
- original task/spec identity;
- protected authority instructions;
- a configurable recent verbatim window.

Middle history MAY use observation elision, external archival, selective recall, and summarization.

### 4.1 Staged compaction
A candidate default policy SHOULD:
1. measure context pressure;
2. at a soft threshold, elide bulky stale observations into content-bound stubs;
3. at a hard threshold, summarize the oldest eligible middle events;
4. preserve recent turns verbatim.

Summarization SHOULD NOT precede cheaper deterministic elision unless an experiment justifies it.

### 4.2 Compaction provenance
Every compacted event MUST retain original event identity, content hash, compaction action, compaction revision, and recoverability state.

### 4.3 Recall
If recall is enabled, measure availability, attempts, successful recalls, recalled bytes/tokens, and outcome contribution.

Unused recall machinery SHOULD be eligible for controlled removal.

## 5. ActionInterfacePolicy

RESIDUAL SHOULD support capability-qualified action profiles such as:
- structured_safe;
- hybrid;
- shell_dominant.

The profile determines interaction vocabulary, not authority.

Shell-dominant operation MUST remain subject to the same filesystem scope, sandbox boundary, network policy, process limits, write scope, approvals, evidence capture, and verification.

## 6. Read-before-write identity binding

A mutable file SHOULD NOT be edited or overwritten unless:
1. the worker read the relevant state in the current candidate session or received an equivalent host-certified snapshot;
2. the host records the content hash used as the edit basis;
3. the pre-write hash still matches, unless an explicit merge/rebase path is authorized.

Concurrent or external modification MUST produce conflict or UNKNOWN rather than silently applying against stale state.

## 7. Immediate post-edit diagnostics

After an eligible source edit, RESIDUAL SHOULD run the cheapest relevant deterministic diagnostics before expensive broad verification.

Diagnostics MUST be read-only, bounded, attributable, and attached to candidate evidence.

A cheap diagnostic failure SHOULD return to the repair loop before broader tests consume budget.

## 8. Stagnation detection

The host SHOULD fingerprint consecutive actions using:
- action/tool identity;
- normalized arguments;
- result status;
- failure identity;
- candidate/check identity when relevant.

A bounded reminder MAY be issued after an initial repetition threshold. A larger repeated-failure threshold SHOULD park or terminate the attempt with explicit stagnation evidence.

Another model call is not progress when the same state is reproduced.

## 9. TrajectoryStage

Worker trajectories SHOULD expose host-owned stages such as:
- understand/localize;
- reproduce;
- edit/write;
- deterministic_diagnostic;
- verify;
- repair;
- blocked_authority;
- context_pressure;
- complete;
- other.

Inferred research labels MUST retain provenance and MUST NOT become authority signals.

## 10. FailureMode

Harness-policy diagnosis SHOULD distinguish at least:
- premature_termination;
- context_overflow;
- localization_stall;
- no_edit;
- interface_mismatch;
- static_edit_failure;
- verification_failure;
- repair_stagnation;
- redundant_verification;
- budget_exhaustion;
- authority_denial;
- unknown.

Harness-policy changes SHOULD target the observed failure mode rather than aggregate success rate alone.

## 11. HarnessPolicyImprovementTask

M6/M6.2 MAY generate a HarnessPolicyImprovementTask binding:
- evidence snapshot hash;
- current HarnessProfile hash;
- diagnosed failure mode;
- one primary harness dimension;
- proposed profile delta;
- protected invariants;
- parent/challenger evaluation plan;
- expected mechanism;
- falsifier;
- cost metrics;
- regression set.

Only one primary harness dimension SHOULD change per causal experiment unless a preregistered factorial design says otherwise.

## 12. Champion/challenger evaluation

A candidate HarnessProfile MUST be compared with the current champion under matched tasks, model/provider identity, context budget, source/workload, verifier, authority envelope, execution budget, and acceptance criteria.

A candidate MAY become champion only if:
- safety/authority invariants remain intact;
- required evidence is complete;
- paired outcome improves under the preregistered objective;
- unacceptable regressions are absent;
- cost and latency changes are reported.

Lower cost alone MUST NOT justify materially worse correctness outside preregistered tradeoff bounds.

## 13. Qualification scope

HarnessProfile superiority is valid only for its qualification key.

Material changes in model, provider, model revision, task class, context budget, runtime, or evaluator MUST trigger requalification before reuse of the optimization claim.

## 14. Harness complexity budget

Each optional harness mechanism SHOULD report:
- usage rate;
- token/model-call cost;
- latency;
- outcome contribution from controlled ablation.

A component that is rarely used and yields no measurable benefit SHOULD become eligible for pruning.

More harness machinery is not automatically better harness quality.

## 15. Required telemetry

Adaptive-harness experiments SHOULD retain:
- accepted outcome;
- trajectory length;
- stage at termination;
- tool/action counts;
- re-patch count;
- action-granularity proxy;
- planning updates;
- context pressure over time;
- elision, summarization, and recall events;
- stagnation events;
- deterministic diagnostic failures;
- verification calls;
- token/byte/cost accounting completeness.

## 16. Minimum acceptance tests

### HADAPT-R1 — Authority invariance
Changing HarnessProfile cannot increase WorkerContract authority.

### HADAPT-R2 — Read-before-write
A stale or unread file edit is rejected or routed to explicit conflict handling.

### HADAPT-R3 — Post-edit ordering
Cheap deterministic diagnostics execute before configured broad verification after an eligible edit.

### HADAPT-R4 — Repeated-action stagnation
Repeated identical failing actions produce a bounded reminder/stop path without consuming the full attempt budget.

### HADAPT-R5 — Preamble preservation
Context compaction cannot elide protected system/task/authority preamble.

### HADAPT-R6 — Recent-window preservation
Configured recent turns remain verbatim during middle-history compaction.

### HADAPT-R7 — Elision before summarization
Under the staged policy, soft-threshold elision occurs before a hard-threshold summarization call.

### HADAPT-R8 — Compaction provenance
Every compacted event retains original identity/hash and compaction provenance.

### HADAPT-R9 — Recall telemetry
If recall is enabled, availability and actual usage are separately measurable.

### HADAPT-R10 — Planning ablation
Planning-on vs. planning-off profiles can be compared while model, task, context policy, action interface, and evaluator remain fixed.

### HADAPT-R11 — Action-profile ablation
Structured vs. alternate action profiles can be compared without changing the authority envelope.

### HADAPT-R12 — Failure-stage telemetry
Runs terminating before edit, during repair, from context overflow, or after redundant verification are distinguishable in retained evidence.

### HADAPT-R13 — Paired champion/challenger
A harness-policy candidate cannot become champion without matched evaluation against the current profile.

### HADAPT-R14 — Cross-model invalidation
Changing model identity invalidates reuse of an old harness-superiority certificate until requalification.

### HADAPT-R15 — Complexity pruning
An optional component with zero observed use remains removable without changing protected authority state.

### HADAPT-R16 — UNKNOWN remains UNKNOWN
Missing accounting, ambiguous state, or unavailable evaluation cannot promote a HarnessProfile.

## 17. Recommended research sequence

1. Instrument trajectory/failure stages.
2. Standardize read-before-write identity binding.
3. Add deterministic post-edit diagnostic ordering.
4. Add repeated-tool-call stagnation evidence.
5. Add staged context compaction.
6. Add explicit HarnessProfile identities.
7. Run planning and action-interface ablations on RESIDUAL workloads.
8. Add Scientist-generated HarnessPolicyImprovementTasks.
9. Add champion/challenger profile promotion.
10. Re-run qualification after model/provider changes.

## 18. Claims boundary

Implementing this spec would establish an adaptive harness experimentation framework.

It would not establish a universally optimal planning policy, universal superiority of shell-only tools, transferability of the paper's thresholds, uselessness of recall, capability from model size alone, autonomous authority expansion, or universal self-improvement.
