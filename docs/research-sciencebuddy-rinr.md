# ScienceBuddy (arXiv:2609.17523) — Findings Most Useful to RESIDUAL

**Paper:** *ScienceBuddy: Recursive-in-Recursive Self-Improvement for Interactive Scientific Agents*  
**Version reviewed:** arXiv v1, 2026-09-15  
**Source:** https://arxiv.org/abs/2609.17523  
**Review date:** 2026-09-18

## Bottom line

The paper is unusually relevant to RESIDUAL because it separates two improvement mechanisms that RESIDUAL is also beginning to distinguish:

1. **procedural / harness improvement with model weights fixed**, and
2. **model improvement under a fixed harness**.

The strongest transferable result is not the RL method. It is the **experimental control discipline around harness evolution**: freeze the task model, freeze evaluators, restrict each edit, compare parent and candidate under paired conditions, keep successful historical cases in the regression set, separate adaptation from validation, retain rejected candidates, and re-evaluate inherited procedures when the model changes.

Those ideas directly strengthen M6/M6.2 without granting recursive authority.

## Most useful findings

### 1. Harness improvement can be isolated from model improvement

ScienceBuddy's inner recursion keeps the task model fixed while a separate fixed auxiliary model diagnoses trajectories and proposes procedural edits. The paper reports a validation increase from **31.1% to 51.1%** with model weights unchanged.

**RESIDUAL implication:** M6 should treat procedure quality as an independently measurable variable. A stronger model must not be the default explanation or remedy for a failed self-maintenance experiment.

### 2. Improvement proposals should be bounded and structurally validated

The paper permits one scoped skill edit, instruction edit, or exposed context-setting change per proposal. Tools, execution infrastructure, rubrics, and evaluators stay fixed.

**RESIDUAL implication:** the Scientist / improvement-discovery role should emit one bounded hypothesis or one bounded procedure change at a time. It must not be able to change the verifier, receipt schema, authority boundary, test oracle, promotion rules, or evidence that will judge it.

### 3. Parent and candidate should be evaluated under identical conditions

ScienceBuddy evaluates both under the same development tasks, seeds, execution budgets, and frozen rubrics. A candidate is accepted only if valid and better than its parent.

**RESIDUAL implication:** M6 needs a first-class paired parent/candidate protocol. A candidate should not be promoted from an unpaired "it passed once" result.

### 4. Previously successful tasks belong in the regression set

The paper explicitly includes previously successful tasks during recursive evaluation to catch regressions.

**RESIDUAL implication:** an improvement that fixes the current failure but breaks a previously accepted path is not an improvement. The acceptance contract should include protected historical wins.

### 5. Adaptation, validation, and final test evidence must stay separate

Harness edits are driven by an adaptation/development set, then evaluated on a separate validation set. The final held-out test set is not used for editing or selection.

**RESIDUAL implication:** M6 discovery evidence, candidate-selection evidence, and confirmatory evidence should be separate hash-bound sets. This is especially important because RESIDUAL already retains rich failure traces that could otherwise leak into the evaluation set.

### 6. User / execution interaction can be compiled into tasks and rubrics

ScienceBuddy turns requests, replies, actions, observations, and artifacts into executable tasks plus evaluation rubrics.

**RESIDUAL implication:** RESIDUAL can formalize a missing bridge between Evidence Bus records and M6.2 ImprovementSpecs: evidence can produce either an **ImprovementTask** with a frozen rubric or a **MeasurementGap** when evidence is insufficient. This is compatible with the epistemic fork already explored in M6-EPI-001.

### 7. Rejected edits are still useful evidence

Rejected candidates and score changes remain in history even when they are not selected as the next parent.

**RESIDUAL implication:** keep failed improvement hypotheses as evidence for diagnosis and stagnation detection, but do not silently make them eligible parents. This complements the repair-stagnation work already underway.

### 8. Difficulty should evolve only after current tasks become routine

ScienceBuddy calibrates task difficulty under the current model+harness and augments tasks when old ones stop being informative.

**RESIDUAL implication:** a future challenge-frontier generator can create harder variants, but generated tasks must pass an independent validity gate and must never rewrite their own evaluator. This is useful for M6 once fixed ImprovementSpec trials become too easy.

### 9. A harness must be re-qualified after the model changes

The paper re-evaluates an inherited harness after updating the task model because harness effectiveness is model-dependent.

**RESIDUAL implication:** procedure superiority is not timeless. Any model/provider/toolchain revision that can affect behavior should invalidate the "candidate > parent" certification unless the pair is re-evaluated.

### 10. Recursive improvement can be asynchronous with serving

ScienceBuddy keeps the online service running while background improvement proceeds.

**RESIDUAL implication:** M6 discovery and candidate evaluation should remain a shadow path. Production/main behavior should not change until the ordinary RESIDUAL review, verifier, receipt, integration, maintainer, and release gates are satisfied.

## Findings that should NOT be copied directly

- **GRPO / weight training** is not required for RESIDUAL's near-term roadmap. The transferable idea is the separation of model-learning and harness-learning loops, not the specific RL algorithm.
- The paper's reported gains are **ScienceBuddy-specific** and should not be presented as expected RESIDUAL gains.
- The paper does not solve RESIDUAL's authority problem for us. RESIDUAL should remain stricter: an improvement proposer must never gain acceptance, integration, promotion, merge, or evaluator authority.
- A mean-score increase alone is insufficient for RESIDUAL. Protected regressions, evidence completeness, authority invariants, and fail-closed behavior must remain hard gates.

## Recommended RESIDUAL changes

1. Add a hash-bound **ExperienceSnapshot -> ImprovementTask | MeasurementGap** compiler.
2. Add a read-only, analysis-only **Scientist** role that cannot write, integrate, promote, or modify evaluators.
3. Require **one bounded change dimension per candidate**.
4. Add a **paired parent/candidate evaluator** with identical tasks, seeds, budgets, model/provider revisions, and frozen rubric hashes.
5. Maintain a **protected regression set** containing previously successful cases.
6. Partition evidence into **adaptation**, **selection/validation**, and **confirmatory** sets.
7. Retain rejected candidate history, but prohibit rejected candidates from becoming parents unless an explicit new experiment says otherwise.
8. Add **cross-revision requalification** when model/provider/toolchain identity changes.
9. Add an optional **challenge-frontier** stage for generating harder tasks after current tasks saturate, with independent validity checks.
10. Keep any future model-weight learning behind a separate interface and qualification boundary.

These changes are specified in `docs/specs/SPEC-M6-RINR-001.md`.


## Second-pass findings: additional mechanisms worth carrying into RESIDUAL

A closer reading of the implementation appendix adds five useful design constraints that are easy to miss from the high-level recursive-in-recursive diagram.

### Separate diagnostic feedback from optimization/acceptance reward

ScienceBuddy explicitly separates a bounded feedback-interpreter signal from the trajectory reward used for optimization. User replies can diagnose a procedural weakness without becoming correctness labels.

**RESIDUAL application:** operator/user/reviewer feedback should feed the Scientist's diagnosis, while promotion continues to depend on frozen evaluators, verifiers, receipts, and regression gates.

### Require fresh re-execution after every procedure change

Historical interactions are used for task definition and diagnosis, but policy learning uses fresh rollouts and harness comparisons execute the actual candidate.

**RESIDUAL application:** old traces can generate an ImprovementTask, but cannot prove that a changed procedure works. Parent and candidate should generate fresh, version-bound trajectories under the same evaluation contract.

### Distill procedures, not answers

ScienceBuddy's proposer is instructed not to encode task-specific answers, numerical results, or sample IDs into reusable skills.

**RESIDUAL application:** add a task-local quarantine/generalization classifier so self-improvement converts repeated failure evidence into reusable procedures without turning the harness into a cache of benchmark answers.

### Use different metrics for procedural quality and capability breadth

The paper uses first-response accuracy for harness adaptation and pass@4 problem coverage for model learning. These answer different questions.

**RESIDUAL application:** track first-pass quality, bounded-repair efficiency, problem coverage, accepted-state reliability, regression preservation, and cost separately. A procedure that reduces retries is different from a solver/model change that expands the set of solvable problems.

### Maintain a champion, but avoid false causal attribution

The appendix retains all versions and rejected edits, while deployment follows the selected/best procedure. It also warns that the observed harness gains are the combined effect of successive edits; individual skills were not separately isolated.

**RESIDUAL application:** keep a best-so-far champion procedure and a diagnostic archive of rejected candidates. Periodically run removal/ablation tests before claiming that one accumulated skill caused an improvement; track harness size to detect accretion.
