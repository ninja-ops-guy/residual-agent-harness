# Verified Non-Parametric Continual Learning for Embodied Agents Through OODA-Guided Skill Acquisition

**Working IEEE-style manuscript — experimental protocol draft**

## Abstract
Large language models can select robot tools and synthesize control code, but allowing the same probabilistic component to author, execute, and approve new behaviors creates an authority problem. We propose an architecture for embodied continual adaptation in which an agent acquires persistent executable skills without modifying foundation-model weights. A fast Observe–Orient–Decide–Act (OODA) loop selects existing capabilities; a slower learning loop identifies capability gaps, synthesizes candidate behaviors, subjects them to independent qualification, and promotes only artifacts supported by environment-bound evidence. We implement the architecture as an experimental RESIDUAL integration for Anki Vector using an existing Wire-Pod/MCP control plane. The design separates authorship from acceptance authority, binds qualification to source and environment digests, and records experience in an append-only ledger. We define a controlled evaluation comparing direct LLM-to-tool control, guarded control, and guarded control with persistent verified skill acquisition. This paper states hypotheses and methodology; no empirical performance claims are made before physical trials are collected.

**Index Terms—** embodied agents, continual learning, OODA, LLM agents, robot learning, runtime assurance, MCP, non-parametric learning.

## I. Introduction
Tool-using LLMs can translate natural-language goals into sequences of robotic actions. A more consequential capability is persistent adaptation: when no existing tool composition reliably solves a task, the system can synthesize a reusable behavior and make that behavior available to future decisions. This changes the effective policy of the embodied system without retraining the underlying model.

The central problem is authority. A generated behavior is not trustworthy merely because its authoring model predicts that it is correct. Embodied execution makes false acceptance physically consequential. We ask: **can an embodied agent accumulate a useful hierarchy of persistent skills through closed-loop experience while an independent, fail-closed mechanism retains authority over promotion?**

Our contribution is a testable architecture and protocol for *verified non-parametric continual learning*: dual-timescale OODA loops; a capability boundary over an existing MCP/Wire-Pod interface; source- and environment-bound qualification receipts; persistent outcome evidence; and a three-condition experiment measuring acquisition, reuse, violations, cost, and intervention.

## II. System Model
The physical control path already exposes Vector capabilities through Wire-Pod and MCP. RESIDUAL is inserted above that functioning transport rather than replacing it. The model may propose calls or source artifacts; a guarded session enforces an allowlist, call budget, and mission duration. Candidate code is represented by a BehaviorSpec containing required tools, acceptance obligations, source, and environment.

A qualification receipt binds the candidate canonical digest to an environment digest. The environment SHOULD include robot profile, firmware, Wire-Pod revision, MCP schema, SDK/runtime, and policy version. Any change invalidates receipt currency until requalification. A candidate cannot be accepted without independent tests and a hardware probe. The authoring agent has no interface that directly sets acceptance.

## III. Dual OODA Learning Architecture
The fast loop performs Observe→Orient→Decide→Act for current tasks. Orient queries the capability registry and prior evidence. When Decide can satisfy the task with a qualified behavior, Act invokes it under policy.

The slow loop operates over outcomes: observe recurring failures or inefficiencies; orient to a capability gap; decide whether a reusable behavior is warranted; synthesize a candidate; qualify it independently; canary it physically; and only on acceptance register it for subsequent fast-loop calls. Learning is therefore persistent behavioral acquisition rather than parameter updating.

This definition is deliberately narrower than weight-based continual learning. The model can remain unchanged while the composite system's reachable policy changes because its verified callable repertoire changes. Skills may compose qualified lower-level skills, producing a provenance-carrying hierarchy.

## IV. Safety and Trust Boundary
Four invariants are required: authorship and acceptance authority are separate; unknown capabilities fail closed; qualification is artifact- and environment-specific; and evidence is retained independently of model narrative. Physical canaries SHOULD begin with bounded low-energy actions, conservative motion/time budgets, and a human-accessible stop. Protections below the LLM layer remain authoritative. This work does not claim regulatory certification; “qualified” means a specific artifact satisfied a declared RESIDUAL profile in a declared environment.

## V. Experimental Design
Compare three conditions with the same model family, task corpus, robot, environment, and tool surface: **A**, direct LLM→MCP; **B**, RESIDUAL guarded MCP without persistent learned behaviors; **C**, guarded control plus persistent independently-qualified behavior acquisition. Randomize task order. A held-out set contains tasks whose useful composite behavior is absent initially but expressible using permitted primitives.

Primary outcomes are held-out task completion and unauthorized/unsafe call attempts. Secondary outcomes include human interventions, wall time, inference tokens, MCP calls, repair iterations, qualification false acceptance, behavior reuse, regressions after controlled dependency drift, and amortized cost after acquisition. Every trial retains OODA events and raw evidence.

### A. Hypotheses
**H1:** persistent qualified skill acquisition increases effective task capability across repeated/related held-out tasks relative to a non-persistent guarded system.

**H2:** independent qualification reduces false acceptance and unauthorized execution relative to direct model-controlled execution.

**H3:** after acquisition cost is paid, reuse reduces inference/tool-call cost on related tasks.

**H4:** environment-bound receipts prevent stale behaviors from silently retaining qualified status after controlled dependency changes.

### B. Avoiding Circular Evaluation
The model that authors a candidate MUST NOT be the sole judge of acceptance. Wherever possible, acceptance predicates are frozen before generation and evaluated using deterministic assertions, observable robot state, independent telemetry, or retained human labels. LLM judging, if studied, is a separate noisy measurement rather than ground truth.

### C. Statistical Plan
Report raw trials, sample sizes, effect sizes, uncertainty intervals, and failure categories. Binary outcomes SHOULD use binomial intervals and paired analyses where tasks match across conditions. Time/token/call distributions SHOULD use robust summaries and paired bootstrap intervals. Freeze protocol, task corpus, exclusions, and primary endpoints before confirmatory trials; label exploratory iterations separately.

## VI. Ablations
Ablate persistence, independent qualification, environment binding, outcome memory, skill composition, and policy budgets. A key negative control synthesizes skills but discards them after each episode, separating gains from extra inference from gains attributable to persistent acquisition. Another deliberately changes Wire-Pod/MCP environment identity to test stale-receipt rejection.

## VII. Threats to Validity
A single Vector platform limits hardware generalization. MCP tool quality can dominate results. Author-designed tasks can leak implementation assumptions. One model can confound architecture with model-specific tool behavior; many models increase variance. Battery, localization, lighting, network, and mechanical-state drift must be logged rather than silently normalized away.

## VIII. Discussion
The system is learning at the composite-agent level, not claiming model-weight learning. Experience changes a persistent, qualified action vocabulary. This resembles procedural memory/library learning with an explicit authority boundary: generation proposes capability changes; evidence determines whether they become executable.

Dual loops separate immediate adaptation from evolution. Fast OODA solves the present task. Slow OODA asks what reusable capability would improve future tasks, then qualifies that proposal. The lifecycle can support acquisition, challenge, degradation, quarantine, supersession, and retirement rather than treating generated code as permanently trusted.

## IX. Conclusion
We present a falsifiable approach to embodied continual adaptation in which LLM-authored behaviors can become persistent robot skills without allowing the authoring model to certify its own output. Vector/Wire-Pod/MCP provides a physical testbed for evaluating whether verified skill accumulation improves capability and efficiency while preserving explicit authority boundaries. Next: freeze tasks and qualification profile, run randomized physical trials, and report successes and failures without converting exploratory evidence into confirmatory claims.

## References
Submission references will be populated from verified primary literature for OODA, continual/robot learning, runtime assurance/shields, behavior/skill libraries, MCP, Wire-Pod, and RESIDUAL. References are intentionally not fabricated in this working draft.
