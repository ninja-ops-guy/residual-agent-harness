# PRIOR-ART-MATRIX — Adversarial Prior-Art Review for EXP-M6-SLM / SLM-05

**Scope of review:** Research question under review: *"How does progressively externalizing agent cognition into deterministic control infrastructure change the minimum model capacity required to achieve a fixed level of verified autonomous task performance?"*
Central experiment (SLM-05): ablate harness machinery (structured state, contracts, epistemic memory, deterministic verification, failure/repair history) for a small control-plane decision model (StationLM 150–400M, Residual-Nano 30–80M) and measure the leftward shift in minimum model capacity at a preregistered verified-performance threshold.

**Method:** adversarial web/scholar search across LLM/SLM routing, model cascades, cost-aware inference, specialist LMs, agent control planes, deterministic scaffolding, external memory, tool use, neuro-symbolic systems, structured protocols, verifier guidance, learned orchestration, model escalation, calibration routing, inference-time scaffolding, and capability externalization. Searches explicitly targeted duplicating/contradicting work, not just support.

---

## 1. Threat-tier summary (read first)

**Tier 1 — Direct structural overlap with the RESIDUAL architecture (deterministic control plane over an LLM/SLM):**
- **Rel(AI)Build — "A Deterministic Control Plane for LLM Coding Agents"** (arXiv:2606.26924, June 2026). The single closest architectural prior art found. It explicitly proposes a deterministic control plane *above* the agent harness: deterministic install-time gates, attack-derived blocklists enforced *before LLM invocation*, phase state machines with requirement→file→test traceability, hash-chained audit logs — and states verbatim that governance of this layer "must be deterministic and tool-agnostic — not delegated to further LLM orchestration." This duplicates the RESIDUAL authority/contract/determinism design philosophy. **Material difference:** it does not use a *small model as the decision element inside the loop*, does not ablate harness machinery, and does not measure capacity-shift. It duplicates the *architecture*, not the *experiment*.

**Tier 2 — Duplicates the *measured phenomenon* (scaffolding/capability externalization lets small models match large ones) at larger scale:**
- **"Three Roles, One Model"** (arXiv:2604.11465, Apr 2026): Qwen3-8B on AppWorld; a three-tier inference scaffold (summarizer / agent / isolated corrector roles on frozen weights) doubles task completion (5.4%→8.9%), beating a 33B baseline; includes systematic failure-mode analysis showing scaffolding eliminates "mechanical" failures and "unmasks" residual reasoning limits. This is the strongest empirical precedent that structured scaffolding substitutes for ~4× model scale. **Material difference:** single model size (8B), no capacity-sweep, no *deterministic* verifier (the corrector is the same LLM), no preregistered threshold, no ablation-derived capacity curve. It demonstrates the effect but does not measure the dose-response (capacity × harness-machinery) relationship SLM-05 targets.
- **DSPy** (Khattab et al., 2023, arXiv:2310.03714): compiled pipelines make T5-770M / Llama2-13B competitive with GPT-3.5 prompt chains. Closest precedent for "systematic scaffolding shifts the capacity requirement downward," including small-model specialization.
- **Toolformer** (Schick et al., 2023): GPT-J 6.7B with self-taught tool use beats GPT-3 175B on arithmetic/factual tasks — canonical "capability externalization shifts capacity threshold" result.
- **NVIDIA position paper — "Small Language Models are the Future of Agentic AI"** (Belcak et al., 2025, arXiv:2506.02153): explicitly argues SLMs (<10B) are sufficient, more suitable, and more economical for most agentic invocations when embedded in heterogeneous agentic systems; proposes an LLM→SLM agent conversion algorithm. This paper **stakes out the thesis of SLM-05 at the position level**; SLM-05's defensible residue is the *preregistered ablation-quantified capacity curve at 30–400M scale with deterministic verification*, which the position paper does not measure.

**Tier 3 — Routing/cascade literature (partial overlap, mostly orthogonal mechanism):** FrugalGPT, RouteLLM, Hybrid-LLM, AutoMix, RouterBench/RouterEval, routing surveys. These substitute cheap models for expensive ones per-query via *learned routing/self-verification*, i.e., they externalize the "which model" decision rather than cognition itself. They narrow any claim phrased as "small models can do X under infrastructure" (established), but none measures the capacity-vs-harness-machinery trade-off curve for a *fixed verified agentic threshold*.

**Tier 4 — Standard agent scaffolding/memory/protocol baselines (crowded field, low novelty threat to the general idea):** ReAct, Reflexion, Self-Refine, MRKL, HuggingGPT/JARVIS, AutoGen, Gorilla, MemGPT, constrained decoding (Outlines/XGrammar/llguidance), AutoPyVerifier. These collectively establish that external memory, tool use, self-verification, and structure raise small-model performance — so the *directional* claim of SLM-05 is not novel. The specific claim must rest on the capacity-shift measurement and determinism guarantees.

---

## 2. Per-work matrix

### A. Routing / cascade / cost-aware inference

**A1. FrugalGPT**
- Citation: Chen, Zaharia, Zou, "FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance," arXiv:2305.05176 (May 2023), Stanford.
- Research question: how to use LLM APIs within a budget while matching best-model performance.
- Model sizes: GPT-J 6B → J1-Large → GPT-3/ChatGPT/GPT-4 cascade; DistilBERT scorer.
- Harness/scaffolding: LLM cascade with learned DistilBERT regression scorer; prompt adaptation; LLM approximation (fine-tuned cheap models).
- Benchmark: HEADLINES, COQA, etc. Routing mechanism: learned per-query cascade with acceptance thresholds. Verification mechanism: learned scorer (not deterministic). Economic: up to 98% cost reduction, +1.5–4% accuracy. Safety: none.
- Relationship to SLM-05: demonstrates cheap-model-first substitution under an external evaluator. Overlap: "small model + external machinery matches large model." Material difference: static QA routing, no agentic control plane, no capacity sweep, no determinism. Weakens novelty of any loose "small+cheap suffices" claim: **yes, mildly**. Unresolved: does a deterministic (vs learned scorer) verifier shift the cascade floor further left?

**A2. RouteLLM**
- Ong, Almahairi, Wu, Chiang, Wu, Gonzalez, Kadous, Stoica, "RouteLLM: Learning to Route LLMs with Preference Data," arXiv:2406.18665 (Jun 2024), ICLR 2025, Berkeley/Anyscale.
- Question: cost/quality trade-off via single-hop routing between strong/weak LLMs using Chatbot Arena preference data + augmentation.
- Models: GPT-4 vs Llama-3-8B-class pairs; BERT/matrix-factorization routers. Benchmarks: MT-Bench, MMLU, GSM8K; >2× cost savings, OOD generalization. Verification: none (preference prediction). Safety: none.
- Relationship: learned routing ≠ cognition externalization; no verified task-performance threshold. Weakens novelty: low (mechanism different). Unresolved: none for SLM-05 core.

**A3. Hybrid-LLM**
- Ding et al., "Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing," arXiv:2404.14618 (Apr 2024).
- Edge/small (OPT-1.3B/BART, Llama-2-13B) vs cloud LLM; router estimates response-quality gap with uncertainty; 40% of queries routed to small model at <1–3% quality drop.
- Relationship: establishes capacity-substitution frontier for single queries. No agentic verification; BARTScore-based labels. Weakens novelty: low.

**A4. AutoMix**
- "AutoMix: Automatically Mixing Language Models" (2023–24; per secondary sources): small model self-verifies its answer via confidence/meta-cognition, escalates to larger LLM. Overlap: verifier-guided escalation. Material difference: verification is *the model itself* (non-deterministic). Weakens novelty: low-moderate; SLM-05's deterministic verifier is a distinguishing axis.

**A5. RouterBench (Hu et al., arXiv:2403.12031, Mar 2024) and RouterEval (Huang et al., 2025); routing survey arXiv:2603.04445 (2026)**
- Establish routing as a benchmarked, surveyed field with six paradigms (difficulty-aware, preference, clustering, RL, uncertainty, cascade). Significance: SLM-05 must not be framed as "routing" — that space is saturated; the harness-ablation capacity-curve framing must be foregrounded.

### B. Tool-using agents / specialist models / orchestration

**B1. Toolformer** (Schick, Dwivedi-Yu, Dessì, Raileanu et al., Meta, arXiv:2302.04761, Feb 2023; NeurIPS 2023).
- GPT-J 6.7B self-supervised API-call insertion; beats 175B GPT-3 on ASDiv/SVAMP/MAWPS, LAMA. Verification mechanism: perplexity-improvement filter at training time. **Key prior demonstration that tool externalization substitutes for ~25× parameters.** Overlap: high with the directional thesis. Material difference: tools are invoked by the model, no deterministic authority layer, no capacity sweep, no verified agentic threshold. Weakens novelty: **yes — of the broad claim; not of the measured curve.**

**B2. ReAct** (Yao et al., Google/Princeton, arXiv:2210.03629, Oct 2022; ICLR 2023).
- Interleaved reasoning+acting; PaLM-540B on HotpotQA/FEVER/ALFWorld/WebShop. Established the thought-act-observe control loop every harness implements. No capacity question asked. Weakens novelty: background threat — ReAct-style prompting is presumed baseline machinery.

**B3. Reflexion** (Shinn et al., arXiv:2303.11366, Mar 2023).
- Verbal RL; binary/scalar environment feedback → episodic memory; ~+11–30 pts on ALFWorld/HumanEval. Direct precedent for *failure/repair history* (an SLM-05 ablation axis) improving agents. Material difference: memory is natural-language reflection stored by the model, not deterministic epistemic memory. Weakens novelty: moderate for the memory axis.

**B4. Self-Refine** (Madaan et al., arXiv:2303.17651, Mar 2023). Single LLM feedback/refine loop, +~20% absolute on 7 tasks, GPT-3.5/4. No determinism, no capacity question. Low threat; cites expected.

**B5. HuggingGPT/JARVIS** (Shen, Song, Tan, Li, Zhu et al., Microsoft/ZJU, arXiv:2303.17580, Mar 2023; NeurIPS 2023).
- LLM-as-controller planning over expert models; four-stage pipeline. **Architectural ancestor of "model proposes, station decides" — but the controller is the large model, and no deterministic authority/verification exists.** Weakens novelty: moderate (control-plane language precedent); strengthens differentiation on determinism+SLM decision core.

**B6. AutoGen** (Wu et al., Microsoft, arXiv:2308.08155, Aug 2023). Multi-agent conversation framework; code execution; human-in-loop. General orchestration substrate; no determinism guarantees, no capacity study. Low novelty threat; high "crowded field" threat.

**B7. Gorilla** (Patil, Zhang, Wang, Gonzalez, arXiv:2305.15334, May 2023). Fine-tuned LLaMA-7B with retrieval-grounded API calling beats GPT-4 on APIBench; constraint-aware API selection. Precedent for specialized SLM reliability in structured action spaces. Moderate overlap with "specialist SLM"; no verification determinism.

**B8. MRKL** (Karpas et al., AI21, arXiv:2205.00445, May 2022). Modular expert routing with a symbolic/LLM router ("model proposes, router dispatches" ancestor). Historical anchor only.

### C. Control planes / deterministic scaffolding / verification

**C1. Rel(AI)Build — "A Deterministic Control Plane for LLM Coding Agents" (arXiv:2606.26924, Jun 2026).**
- Authors: per arXiv listing (Node.js reference implementation). Question: governance layer above agent harnesses for coding agents.
- Mechanisms: SHA-256 content addressing, HMAC lockfiles, hash-chained audit logs, tiered permissions + attack-derived blocklists enforced **pre-LLM-invocation**, phase state machine with requirement→file→test traceability, IDE-target compilation, Jaccard drift detection. Validation: conformance tests on injected violations (determinism confirmed); developer outcomes = future work.
- **Relationship to SLM-05: closest found.** Duplicates the deterministic authority/contract/audit design space and the "governance must not be delegated to LLM orchestration" principle. Material differences: (a) the decision model inside its loop is a frontier LLM, not a 30–400M SLM; (b) no ablation of control-plane components; (c) no minimum-capacity measurement; (d) no verified-performance threshold or economics. **Weakens novelty of the architecture: substantially. Weakens novelty of the central experiment (capacity-shift quantification): no.** Unresolved: is RESIDUAL's determinism claim distinguishable in writing, or is a citation+delta section mandatory? (Answer: mandatory.)

**C2. AutoPyVerifier** (Megagon Labs, arXiv:2604.22937, Apr 2026). DAG search over compact *deterministic executable verifiers* for LLM outputs (math/code/function-calling/instruction-following); +55 F1 over LLM-generated verifier sets; verifiers-as-tools give +17 pts. **Direct evidence that deterministic executable verification beats LLM self-verification** — supports SLM-05's verifier axis but also means "deterministic verification helps agents" is established. Weakens novelty: moderate on the verifier axis.

**C3. Constrained decoding stack** — Outlines (Willard & Louf, 2023), XGrammar (Dong et al., 2024), llguidance (Microsoft, 2024); survey arXiv:2501.10868. Grammar/schema-constrained generation makes structural validity *guaranteed, not probabilistic* — i.e., one SLM-05 "contract" axis is already commoditized at the decoding layer. SLM-05 contracts must be shown to go beyond syntax (semantic authority, evidence). Low novelty threat if contracts are framed as semantic/authority, not schema.

### D. Inference-time scaffolding / capability externalization / SLMs-as-agents

**D1. "Three Roles, One Model"** (McClendon, Gallego-Feliciano, Zervoudakis, Saravanos, arXiv:2604.11465, Apr 2026). Detailed above (Tier 2). **Strongest empirical threat:** quantified demonstration that structured scaffolding substitutes for ~4× model scale on a verified agentic benchmark (AppWorld), with failure-mode taxonomy ("mechanical" vs reasoning failures) closely paralleling RESIDUAL's contract/state machinery rationale. Material differences: one size (8B), same-LLM corrector (non-deterministic), no ablation-driven capacity curve, no preregistration, no nano-scale models. **Recommendation: mandatory head-to-head citation; SLM-05's claim must be the *curve*, not the *effect*.**

**D2. NVIDIA position paper: "Small Language Models are the Future of Agentic AI"** (Belcak et al., NVIDIA, Jun 2025, arXiv:2506.02153). Argues SLMs (<10B) are sufficiently powerful, operationally more suitable, necessarily more economical in agentic systems; heterogeneous LLM+SLM architectures; LLM→SLM conversion algorithm. Position-level, not experimental. **This paper owns the headline thesis.** SLM-05 survives as the *quantified, ablated, preregistered capacity-shift measurement at 30–400M*, which is exactly what the position paper lacks. Weakens novelty: **of the framing, yes; of the experiment, no.**

**D3. DSPy** (Khattab et al., Stanford, arXiv:2310.03714, Oct 2023). Compiled declarative pipelines; T5-770M / Flan-T5-large competitive with GPT-3.5 pipelines via teleprompter optimization and BootstrapFinetune distillation. Demonstrates pipeline structure + compilation shifting capacity floor to sub-1B. Material difference: optimization is learned prompts/finetunes, not deterministic runtime authority; no verified-threshold capacity sweep. Moderate novelty threat; must be cited.

**D4. MemGPT** (Packer et al., UC Berkeley, arXiv:2310.08560, Oct 2023). OS-style external memory hierarchy; LLM pages memory via function calls. Precedent for *structured state/epistemic memory externalization* (two SLM-05 ablation axes). Difference: memory ops chosen by the model, not deterministic station-managed state. Low-moderate threat.

**D5. evoGraph** (arXiv:2508.05199, 2025). Specialized SLMs (Phi-2 2.7B, Nemotron-H 4.8B) as mutation operators under a central controller with safety constraints and fitness optimization for legacy-code modernization; cites the NVIDIA position. Additional precedent for "SLM inside deterministic-ish control loop with central controller." Moderate architectural overlap; no capacity ablation.

### E. Neuro-symbolic / structured protocols / surveys
- Neuro-symbolic planning (SayCan lineage, LLM+P, grammar-constrained generation above): LLM proposes, symbolic planner/verifier decides — conceptually identical division of labor to RESIDUAL; SLM-05 should cite LLM+P (Liu et al., 2023) explicitly; threat is conceptual-ancestor, not experimental duplication.
- Surveys of SLM capabilities and routing (arXiv:2603.04445; "small model agents" surveys 2025) confirm the small-model-agent space is heavily surveyed in 2025–2026; any novelty claim must be narrow and experimental.

---

## 3. Aggregate assessment

**What prior art collectively establishes (cannot be claimed as novel):**
1. Small models + tools/structure can match far larger models on bounded tasks (Toolformer, DSPy, Gorilla, Three-Roles).
2. Deterministic governance/control planes over agent harnesses are desirable and buildable (Rel(AI)Build; constrained decoding; AutoPyVerifier).
3. SLMs are *positionally* argued to be the future of agentic AI (NVIDIA).
4. Routing/cascades already substitute capacity per query (FrugalGPT/RouteLLM/Hybrid-LLM/AutoMix + benchmarks).

**What was NOT found in prior art (candidate residual novelty):**
- No located work sweeps model capacity (30M–400M–large) × *systematic ablation of deterministic harness machinery* (state, contracts, epistemic memory, deterministic verification, repair history) and measures the resulting leftward shift of the minimum-capacity frontier at a preregistered *verified* task-performance threshold.
- No located work uses deterministic (non-learned, non-LLM) verification as the ground truth for the capacity frontier in an agentic setting.
- No located work quantifies *which* harness component buys how much capacity (component-attributed capacity substitution).

**Substantial-duplication flags:**
- Architecture: Rel(AI)Build (C1) — cite and differentiate or risk desk rejection.
- Effect demonstration: Three-Roles (D1) and Toolformer/DSPy (B1/D3) — the unquantified claim "scaffolding lets small models punch above their weight" is taken.
- Thesis: NVIDIA position (D2) — headline claim is taken.

**Recommendation: scope-review gate — NARROW THE CLAIM.** Revise the research question/contribution statement from the general thesis to specifically: "the first preregistered, ablation-attributed measurement of the model-capacity × deterministic-harness-machinery trade-off curve at sub-1B scale under deterministic verification." If SLM-05 cannot deliver a clean capacity×ablation curve with deterministic verification at preregistered thresholds, reject novelty; if it can, split the hypothesis so the architectural determinism contribution is positioned as *building on* Rel(AI)Build-class work, not inventing the category.

NOVELTY STATUS: PARTIAL
