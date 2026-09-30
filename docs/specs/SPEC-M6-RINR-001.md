# SPEC-M6-RINR-001 — Evidence-Grounded Recursive Improvement Without Recursive Authority

**Status:** Proposed  
**Scope:** M6 / M6.2 research and future productionization  
**Source inspiration:** ScienceBuddy, arXiv:2609.17523  
**Primary goal:** let RESIDUAL discover and evaluate improvements from retained evidence without allowing the improvement loop to modify its own authority or acceptance boundary.

## 1. Non-negotiable boundary

RESIDUAL MAY improve procedures, prompts, scoped skills, context policy, planning heuristics, and other explicitly exposed improvement surfaces.

RESIDUAL MUST NOT let an improvement proposer or candidate modify, bypass, or self-satisfy:

- verifier code or verifier policy;
- protected tests or frozen rubrics;
- evidence / receipt schema;
- M4 / Station authority rules;
- review requirements;
- promotion or merge requirements;
- source-scope restrictions;
- budget accounting;
- release eligibility;
- human approval requirements;
- the evidence snapshot used to judge that candidate.

A candidate that requires weakening any of these controls is invalid, not improved.

## 2. Roles

### 2.1 Scientist

The **Scientist** is a read-only analysis role.

It MAY:

- inspect hash-bound execution evidence;
- identify unmet criteria and recurring failure modes;
- cite specific actions, observations, artifacts, checks, and prior candidates;
- propose a falsifiable improvement hypothesis;
- propose a bounded candidate edit description;
- request additional measurement.

It MUST NOT:

- write repository files;
- mutate mission state;
- run integration;
- issue receipts;
- approve review;
- promote a candidate;
- modify rubrics or tests;
- alter authority or budgets;
- merge code.

The Scientist's output is advisory evidence only.

### 2.2 Implementer

An Implementer MAY realize one approved bounded candidate inside the existing isolated worker contract.

It retains exactly the authority of that worker contract and no more.

### 2.3 Evaluator

The Evaluator MUST be independent of the candidate's write scope and MUST consume a frozen evaluation contract.

## 3. Evidence snapshot

Before improvement discovery, the host MUST create an immutable `ExperienceSnapshot`.

The snapshot MUST bind at minimum:

- snapshot ID and SHA-256;
- mission ID and mission revision;
- source revision;
- model/provider identities and configuration;
- task IDs;
- request/spec hashes;
- runner outputs and tool observations;
- verifier/reviewer findings;
- artifact hashes;
- accepted receipts, if any;
- failed/rejected candidate hashes;
- budget/accounting state;
- environment fingerprint;
- collection window;
- evidence completeness status.

The snapshot MUST be append-only once sealed.

Missing required evidence MUST remain explicit.

## 4. Epistemic fork: ImprovementTask or MeasurementGap

Given an `ExperienceSnapshot`, the Scientist MUST emit exactly one of:

1. `ImprovementTask`, when the evidence supports a falsifiable change proposal; or
2. `MeasurementGap`, when the evidence is insufficient.

A `MeasurementGap` MUST identify the missing observation or metric and MUST NOT invent:

- a baseline;
- an effect size;
- a causal explanation;
- a success threshold;
- an acceptance claim.

This preserves the M6.2 rule that insufficient evidence produces a request for measurement, not fabricated certainty.

## 5. ImprovementTask contract

An `ImprovementTask` MUST bind:

- immutable task ID;
- source snapshot hash;
- problem statement;
- evidence citations / record references;
- protected invariants;
- one primary change dimension;
- permitted paths / surfaces;
- forbidden paths / surfaces;
- parent procedure/harness identity;
- candidate success rubric hash;
- paired evaluation plan;
- regression set hash;
- execution budget;
- stop conditions;
- expected falsifier;
- provenance.

The primary change dimension MUST be one of an explicitly registered class such as:

- scoped instruction;
- scoped skill;
- context-selection policy;
- planning heuristic;
- repair-feedback formatting;
- routing heuristic that does not change eligibility/authority.

A task MAY have multiple file edits if they implement one logical change dimension, but MUST NOT bundle unrelated hypotheses.

## 6. Frozen rubric

Each `ImprovementTask` MUST reference a frozen `ImprovementRubric`.

The rubric MUST be created before candidate evaluation and MUST bind:

- criterion IDs;
- executable checks where possible;
- externally judged criteria where necessary;
- criterion weights, if weighted scoring is used;
- hard-gate criteria;
- evidence requirements;
- protected regression criteria;
- evaluator revision;
- rubric hash.

The candidate write scope MUST exclude rubric and evaluator files.

A rubric MUST NOT be revised after candidate outcomes are observed. A changed rubric creates a new experiment identity.

## 7. Data partitioning

Improvement evidence MUST be partitioned into three logical sets:

- **adaptation set** — may inform diagnosis and candidate design;
- **selection / validation set** — may compare parent and candidate but MUST NOT inform candidate editing after outcome access;
- **confirmatory set** — MUST remain unused for diagnosis, editing, or candidate selection until the protocol is frozen.

Task families SHOULD be separated, not merely individual examples, when leakage across near-duplicate tasks is plausible.

Public/developer-authored fixtures MUST be labeled as such and MUST NOT be called independently held out.

## 8. Paired parent/candidate evaluation

Every candidate MUST be compared against its parent under matched conditions.

The pair MUST share:

- task set;
- seed/schedule identity where applicable;
- model/provider identity;
- inference parameters;
- tool environment;
- source baseline except for the candidate delta;
- execution budget;
- rubric hash;
- evaluator revision;
- timeout policy;
- accounting policy.

The evaluation record MUST retain both outcomes.

A candidate MUST NOT be accepted merely because it passed once.

## 9. Acceptance rule

A candidate is eligible to become the next procedural parent only if all of the following hold:

1. scope/schema validation passes;
2. all protected authority invariants pass;
3. all required evidence is complete enough for the declared comparison;
4. no protected regression hard gate fails;
5. paired evaluation shows improvement under the preregistered primary metric;
6. any minimum effect threshold defined before outcome access is satisfied;
7. the candidate does not increase false acceptance or weaken fail-closed behavior beyond frozen limits;
8. review and ordinary RESIDUAL integration/receipt gates pass.

A tie retains the parent.

`UNKNOWN`, missing evidence, incomplete accounting, or evaluator failure MUST NOT become acceptance.

## 10. Protected historical wins

The evaluation set MUST include a regression bank containing previously successful cases relevant to the edited surface.

A candidate that improves the trigger task but breaks a protected prior success MUST be rejected unless the experiment explicitly preregistered a tradeoff rule and that rule does not weaken authority or safety invariants.

Historical PASS and FAIL results remain immutable evidence.

## 11. Candidate and edit history

RESIDUAL MUST retain:

- accepted candidates;
- rejected candidates;
- candidate patch hashes;
- failing check identities;
- score deltas;
- Scientist hypotheses;
- MeasurementGaps;
- repair/stagnation evidence;
- parent-child lineage.

Rejected candidates MUST NOT automatically become parent candidates for later search.

They MAY be used as read-only diagnostic evidence.

## 12. Stagnation

The host SHOULD fingerprint:

- candidate delta;
- failing check IDs;
- failing check kinds;
- relevant evidence snapshot hash.

Repeated identical failed states MUST produce explicit stagnation evidence.

Stagnation MUST NOT be represented as progress simply because another model call occurred.

## 13. Challenge frontier / difficulty calibration

When the active procedure saturates the current adaptation set, RESIDUAL MAY create candidate challenge tasks.

Challenge generation MUST be separated from challenge validation.

A generated challenge task MUST pass an independent validity gate before it is eligible for training/adaptation use.

The generator MUST NOT:

- modify its own evaluator;
- label its own candidate as correct without independent checks;
- place confirmatory tasks into the adaptation set;
- expand worker authority.

Generated challenge tasks SHOULD vary inputs, dependency structure, failure conditions, or context pressure while preserving the original invariant being tested.

## 14. Cross-revision requalification

A parent/candidate superiority decision is valid only for the bound execution context.

If any behaviorally material dependency changes, including:

- model version;
- provider;
- inference policy;
- toolchain;
- runtime environment;
- context policy outside the tested delta;
- verifier/evaluator revision;

the inherited procedure MUST be treated as requiring requalification before its prior superiority claim is reused.

The old result remains historical evidence; it is not deleted or rewritten.

## 15. Asynchronous improvement

Improvement discovery MAY run in the background while the deployed system continues serving with the currently accepted revision.

Background work MUST remain shadow-state only until normal acceptance gates complete.

No background process may silently alter production/main behavior.

## 16. Optional outer model-learning interface

RESIDUAL MAY later support an outer model-learning stage, but it is outside the required implementation of this spec.

If implemented:

- the selected harness/procedure and rubric MUST remain frozen during a model-training stage;
- training data and evaluation data MUST remain separated;
- model updates MUST create a new model identity;
- the inherited harness MUST be re-evaluated with the new model before deployment;
- a model update MUST NOT inherit authority from a prior model;
- training success MUST NOT imply that the improvement mechanism itself became more capable.

No current RESIDUAL claim should imply autonomous weight learning until independently implemented and qualified.

## 17. Diagnostic feedback is not authoritative reward

RESIDUAL MUST distinguish **diagnostic feedback** from **acceptance evidence**.

User/operator feedback, reviewer prose, retry requests, task comments, and other interaction signals MAY identify where a procedure should change. They MUST NOT, by themselves, establish that the preceding candidate was correct or that a proposed improvement succeeded.

Diagnostic feedback SHOULD be classified into bounded types such as:

- acceptance/confirmation;
- correction;
- new information;
- new requirement;
- ambiguity;
- formatting/submission failure;
- execution/tooling failure.

Each diagnostic record SHOULD retain an exact supporting evidence span or event reference.

A successful tool call, a user continuing the task, or a reviewer suggesting a revision MUST NOT be interpreted as authoritative success.

Improvement acceptance MUST remain grounded in the frozen rubric and independent evaluator path.

## 18. Fresh evidence and counterfactual re-execution

Historical trajectories MAY drive diagnosis, but they MUST NOT be the sole evidence that a new procedure works.

After a candidate procedure is proposed, parent and candidate MUST be freshly executed under the paired evaluation contract.

Replay of an old trace MAY test deterministic parsing, accounting, or verifier logic, but MUST NOT be used to claim behavioral improvement by a changed procedure when that procedure did not generate the trajectory.

Each fresh trajectory MUST bind:

- the exact procedure/harness revision;
- the model/provider revision;
- the evaluation task and rubric;
- the environment/source snapshot;
- the run seed/schedule identity where applicable.

This separates **learning from experience** from **proving an intervention**.

## 19. Procedural distillation and task-local quarantine

The Scientist SHOULD convert repeated evidence into reusable procedures only when the proposed procedure abstracts beyond a single task instance.

A proposed reusable skill or instruction MUST NOT encode:

- task-specific final answers;
- private reference values;
- unique sample IDs used only by the source task;
- hidden-test facts;
- evaluator internals;
- literal outputs whose only value is memorization.

Task-specific facts MAY remain in task-local memory/evidence, but MUST NOT be promoted into the reusable harness unless a separate generalization argument and evaluation justify them.

The improvement record SHOULD label each proposal as:

- **general procedure**;
- **domain procedure**;
- **task-local fact**;
- **measurement-only observation**.

Only the first two classes are eligible for reusable harness promotion.

## 20. Objective decomposition and competence-frontier metrics

RESIDUAL SHOULD NOT collapse all recursive-improvement quality into one scalar.

At minimum, it SHOULD distinguish:

- **first-pass quality** — success before repair;
- **repair efficiency** — success after bounded repair and attempts consumed;
- **problem coverage** — distinct problems solved within a fixed attempt budget;
- **accepted-state reliability** — correctness conditional on acceptance;
- **regression preservation** — protected historical wins retained;
- **cost/latency efficiency** — resources per accepted success;
- **epistemic quality** — correct use of MeasurementGap/UNKNOWN instead of invented certainty.

Harness/procedure changes SHOULD primarily optimize first-pass quality, repair efficiency, and accepted-state reliability.

Changes intended to expand underlying solver/model capability SHOULD primarily be judged by problem coverage under a fixed harness and attempt budget.

A change MUST NOT be called an improvement solely because one metric rises while a preregistered hard-gate metric materially degrades.

Challenge generation SHOULD target the **competence frontier**: tasks that are neither already saturated nor so far beyond current capability that they provide no discriminating signal.

## 21. Champion checkpoint and attribution discipline

RESIDUAL SHOULD retain a **best-so-far champion** procedure for each frozen evaluation context.

Experimental candidates MAY be explored from evidence, but the champion remains the deployment/procedural parent unless the candidate satisfies the full acceptance rule.

Rejected candidates remain diagnostic history, not an alternative parent frontier by default.

Because recursive revision compounds multiple accepted edits, aggregate improvement over many steps does not establish which individual edit caused the gain.

Therefore:

- campaign-level gains MUST be described as the combined effect of the accepted revision sequence unless an ablation isolates a component;
- individual skills/instructions SHOULD receive causal credit only after a preregistered ablation or equivalent controlled comparison;
- removal tests SHOULD be used periodically to identify obsolete or harmful accumulated procedures;
- procedure count/size SHOULD be tracked to detect unbounded harness accretion.

This prevents RESIDUAL from confusing cumulative correlation with causal improvement.

## 22. Required metrics

Each recursive-improvement campaign MUST report at minimum:

- paired parent success;
- paired candidate success;
- paired delta;
- regression count/rate;
- false-acceptance count/rate where independently gradable;
- candidate rejection count;
- stagnation count;
- MeasurementGap count;
- distinct problems solved / coverage where meaningful;
- calls/tokens/bytes/cost coverage;
- incomplete-usage count;
- wall time;
- evidence completeness;
- exact source/model/evaluator/rubric identities.

Aggregate averages MUST NOT erase failed, blocked, unknown, or missing cells.

## 23. Minimum acceptance tests for implementation

### RINR-R1 — Snapshot immutability
After sealing an `ExperienceSnapshot`, changing any bound field changes identity or is rejected.

### RINR-R2 — MeasurementGap honesty
Given evidence that omits the required baseline metric, the Scientist path emits `MeasurementGap` and does not emit an `ImprovementTask` containing an invented baseline.

### RINR-R3 — Read-only Scientist
Attempts by the Scientist role to write files, mutate mission state, integrate, approve, receipt, or promote are denied and evidenced.

### RINR-R4 — One change dimension
A candidate that combines unrelated procedure changes is rejected before evaluation.

### RINR-R5 — Frozen rubric
Any post-outcome rubric mutation creates a different experiment identity and cannot retroactively validate the candidate.

### RINR-R6 — Paired conditions
Parent and candidate records must prove identical task, model/provider, budget, evaluator, and rubric identities except for the declared candidate delta.

### RINR-R7 — Regression bank
A candidate that fixes the trigger case while breaking a protected historical PASS is rejected.

### RINR-R8 — UNKNOWN is not improvement
Evaluator failure, missing usage required by policy, or incomplete evidence cannot promote a candidate.

### RINR-R9 — Rejected history retention
Rejected candidate hashes/findings remain queryable but are not selected as parents by default.

### RINR-R10 — Cross-model requalification
Changing the model identity invalidates reuse of the prior parent/candidate superiority certificate until re-evaluation.

### RINR-R11 — Stagnation evidence
Repeated identical failed candidate/check states produce a stagnation record and bounded stop rather than unbounded retries.

### RINR-R12 — Shadow deployment
A successful research candidate cannot change accepted production/main state without the ordinary review, verification, receipt, integration, maintainer, and release path.


### RINR-R13 — Diagnostic/acceptance separation
A positive user/reviewer interaction signal without a passing frozen evaluator MUST NOT promote a candidate.

### RINR-R14 — Fresh intervention evidence
A candidate procedure cannot claim behavioral improvement solely from replaying a trajectory produced by the parent; fresh paired execution is required.

### RINR-R15 — Task-answer leakage prevention
A reusable skill proposal containing a task-specific final answer, private reference value, hidden-test fact, or evaluator internal is rejected or quarantined as task-local.

### RINR-R16 — Objective decomposition
Reports distinguish first-pass quality, repair efficiency, problem coverage, accepted-state reliability, regression preservation, and resource efficiency rather than emitting only one aggregate improvement score.

### RINR-R17 — Champion retention
A non-accepted experimental candidate cannot displace the best-so-far champion procedure.

### RINR-R18 — Attribution restraint
A multi-edit campaign cannot assign causal credit to one skill/instruction unless a controlled ablation or equivalent isolated comparison supports that claim.

## 24. Relationship to current M6.2 work

This spec is intended to organize, not replace, the current M6.2 path.

In particular:

- `ImprovementSpec` remains a useful content-bound artifact.
- M6-EPI evidence-sufficiency vs. measurement-gap behavior becomes normative.
- repair-context and actionable-diagnostic work become inputs to the paired evaluation loop.
- repeated-repair stagnation becomes a required bounded-stop behavior.
- the Scientist is deliberately **analysis-only**.
- successful self-maintenance remains a candidate-generation result until independent acceptance completes.

## 25. Claims boundary

Implementing this spec would establish an **evidence-grounded recursive improvement protocol**.

It would not, by itself, establish:

- autonomous recursive self-improvement;
- model self-training;
- guaranteed monotonic improvement;
- generalization beyond the evaluated task families;
- safe autonomous merge authority;
- universal correctness;
- ScienceBuddy's reported effect sizes on RESIDUAL.

The protocol exists to make those questions experimentally answerable without weakening RESIDUAL's authority model.
