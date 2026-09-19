# Harness Design Study (arXiv:2609.20804) — Findings for RESIDUAL

**Paper:** An Empirical Study of Harness Design for Coding Agents
**Reviewed:** 2026-09-18

## Executive conclusion

The paper's most important lesson for RESIDUAL is that harness design is conditional.

Planning, action interfaces, and context-management mechanisms do not have one universally optimal configuration. Their value changes with model capability, task type, context-window budget, execution cost, and trajectory failure mode.

That changes how RESIDUAL should think about self-improvement. The Scientist should not only ask what code or prompt should change. It should also ask whether the current harness configuration is appropriate for this model, task class, and budget.

## Findings with the highest practical value

### 1. Optimize harness components independently
The study holds the execution loop fixed and separately varies planning, action space, and context management.

**RESIDUAL application:** harness evolution should use component-level ImprovementTasks. Do not bundle planning, tool changes, context policy, prompts, and model changes into one causal experiment.

### 2. Context management is mainly an anti-overflow mechanism
Context-management gains increase as available context shrinks. At large windows, managed and unmanaged trajectories become much more similar.

**RESIDUAL application:** drive context management from observed pressure rather than always-on complexity.

### 3. Cheap elision should precede expensive summarization
The paper's strongest efficiency pattern is staged compaction: remove bulky stale tool output first, summarize only if history is still too large.

**RESIDUAL application:** preserve the control/task preamble and recent turns verbatim, elide stale observations at a soft threshold, and summarize older middle history only at a harder threshold.

### 4. Recoverability must earn its complexity
The paper's recall mechanism was rarely used and showed no consistent accuracy gain over elision alone.

**RESIDUAL application:** measure recall usage and outcome contribution before making lossless recall mandatory.

### 5. Planning should be capability-adaptive
Planning helped the weakest model keep going long enough to attempt an edit. For stronger models, it mainly reduced redundant post-edit verification and cost.

**RESIDUAL application:** planning has at least two distinct jobs: continuation scaffolding and stopping scaffolding.

### 6. Tool richness should depend on worker and task
Structured tools scaffold models with weaker shell control. Shell-capable models can sometimes perform denser operations with fewer interactions and lower cost.

**RESIDUAL application:** qualify action profiles such as structured-safe, hybrid, and shell-dominant without changing the underlying authority envelope.

### 7. Action granularity is an optimization variable
Coarser shell actions often reduced repeated patching.

**RESIDUAL application:** track interaction count, re-patch count, and action granularity per accepted change.

### 8. Read-before-write plus content identity is strong local control
The study rejects edits to unread files and detects external modification with content hashes.

**RESIDUAL application:** candidate edits should be based on a known file identity, not assumed workspace state.

### 9. Fast diagnostics should follow edits immediately
The harness runs cheap read-only static checks after Python edits before broader testing.

**RESIDUAL application:** order verification as edit -> cheap deterministic diagnostics -> targeted tests -> broad verification.

### 10. Repeated identical actions are stagnation evidence
The harness warns after repeated identical calls and terminates repeated failing loops before the full step budget is consumed.

**RESIDUAL application:** extend stagnation detection from candidate/check identity to repeated tool-call identity.

### 11. Trajectory shape is diagnostic
The paper shows different components change different aspects of behavior: context management extends trajectories, planning changes stopping behavior, and action space changes operation granularity.

**RESIDUAL application:** classify where a run fails, not just whether it fails.

### 12. Harness policy must be model/task/budget bound
The paper warns against transferring crossover points directly to other models, tasks, or harnesses.

**RESIDUAL application:** every optimized harness profile should be qualification-bound to model/provider, task class, context budget, action profile, planning policy, context policy, and evaluator revision.

## Self-improvement implication

ImprovementSpec should support harness-policy candidates in addition to code/procedure candidates.

Examples include:
- planning on/off or planning mode;
- context elision threshold;
- summarization threshold;
- optional recall machinery;
- structured/hybrid/shell-dominant action profile;
- cheap-diagnostic sequencing;
- stagnation thresholds.

These remain candidate changes and receive no authority merely because telemetry suggests they might help.

## What should not be copied blindly

- Do not assume bash-only is generally superior for strong models.
- Do not assume the paper's thresholds are optimal for RESIDUAL.
- Do not assume recall is useless in RESIDUAL.
- Do not infer capability from parameter count alone.
- Do not call lower interaction count better if safety or correctness degrades.
- Do not treat the bundled action-space ablation as proof that tool count alone caused the effect.
- Do not treat one run per benchmark task as sufficient production evidence.

Normative requirements are in docs/specs/SPEC-HARNESS-ADAPT-001.md.
