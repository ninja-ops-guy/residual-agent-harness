# Reliability Paper — Related Work Matrix

**Purpose:** define the novelty boundary conservatively before submission.

## Positioning summary

Residual should not claim novelty for model routing, cascades, runtime verification, proof-carrying artifacts, DAG scheduling, caching, or deterministic workflow execution individually. The stronger research contribution is the **composition** of these ideas around a specific acceptance model: potentially unreliable model computation is allowed to propose work, while separate constrained execution, evidence capture, verification, provenance, and deterministic integration determine what may become accepted system state.

## Adjacent work

| Area / work | What it establishes | Residual distinction to test/argue |
| --- | --- | --- |
| FrugalGPT (Chen, Zaharia, Zou, 2023) | Learned/cascade strategies can trade model cost against performance. | Residual's primary variable is not only *which model answers*, but whether a candidate satisfies externally checked obligations before state acceptance. |
| RouteLLM (Ong et al., 2024/2025) | Learned routing between stronger/weaker LLMs can optimize quality/cost. | Routing is subordinate to an acceptance boundary; Residual can reject/escalate based on verifier state and evidence rather than router confidence alone. |
| Rerouting LLM Routers (Shafran et al., 2025) | Treats routers as LLM control planes and shows their integrity can be attacked. | Supports the need to treat orchestration/control decisions as a security boundary; Residual should evaluate control-plane integrity separately from response quality. |
| LLMRouter / xRouteBench (Feng et al., 2026) | Unified routing infrastructure and quality/cost evaluation across multiple routing settings. | Provides a modern routing baseline/benchmark perspective; Residual's claim should remain about verified acceptance and fault containment rather than routing novelty. |
| AgentGuard (Koohestani, 2025) | Runtime verification layer observes agent I/O and reasons about failures under constraints. | Close conceptual neighbor for runtime assurance. Residual additionally emphasizes receipt-bound provenance, obligation-level acceptance, independent final grading, and deterministic integration of candidate state. |
| AWS Dogwood (Brooker, Tassarotti, Tristan, 2026) | Tool-call boundary governance can precisely constrain agent actions at runtime. | Strong prior art for constrained authority. Residual should not claim invention of tool-boundary policy enforcement; it studies whether such constraint plus evidence/verification/integration changes accepted-system reliability. |
| Proof-Carrying Code (Necula, 1997) | Untrusted code may be accompanied by a proof checked by a trusted consumer. | Conceptual ancestor for separating producer trust from acceptance. Residual receipts are not formal proofs and must not be described as such unless a specific verifier produces one. |
| Model checking (Clarke et al.; Baier & Katoen) | Independent formal checking can establish properties of state-transition systems. | Direct lineage for bounded planning/verifier tasks and for treating checking as separate from generation. |
| Byzantine fault tolerance / Lamport et al. | System correctness can depend on protocols tolerating faulty participants. | Motivates component-vs-system reliability analogy, but Residual does not currently claim Byzantine consensus. |
| CEGIS | Candidate generation with counterexample feedback iteratively refines solutions. | Prior art for verifier-guided repair. Residual's distinctive question is how verifier-defined residual work is delegated across heterogeneous model boundaries with evidence/provenance. |
| ReWOO | Separates reasoning from observations/tool outputs and reduces repeated context. | Context/tool separation is prior art; Residual adds obligation acceptance and evidence-bound state transition. |
| LLMLingua-2 | Learned prompt compression. | Residual's scoped evidence packets are not a learned compression claim; evidence intervals and omission/pull semantics serve provenance and verification. |

## Novelty boundary

### Claims that are likely defensible if experiments support them

1. **System-level reliability hypothesis.** Holding the worker model fixed, an evidence-gated acceptance architecture can reduce incorrect accepted state without improving the model itself.
2. **Acceptance-centric evaluation.** Measure `P(correct | accepted)`, false acceptance, coverage, containment, and cost jointly, instead of treating model answer quality as the only reliability variable.
3. **End-to-end composition.** Immutable/bounded worker execution + observation/evidence + independent verification + content-bound receipts + deterministic integration as one control plane for heterogeneous AI work.
4. **Residual delegation with verification-defined frontier.** Escalate only obligations that remain unaccepted, preserving independently verified work and binding cross-model dependencies to evidence/receipt state.
5. **Empirical orchestration-tax controller.** Learn when decomposition/swarming improves net verified utility and when it should be avoided.

### Claims to avoid without stronger evidence

- first agent verification framework;
- first LLM control plane;
- first model router/cascade;
- formal proof of arbitrary agent correctness;
- Byzantine fault tolerance or distributed consensus;
- universal verifier;
- universal production safety;
- state-of-the-art cost/quality performance without matched baselines;
- causal reliability improvement from fixture-only/scripted workers.

## Related-work narrative for the manuscript

The literature can be organized into four layers.

### A. Model selection and cost-aware inference

FrugalGPT and RouteLLM show that heterogeneous models can be composed to improve a quality-cost frontier. Newer routing infrastructure generalizes evaluation across routing formulations. Residual uses these systems as routing baselines, but asks a different question: once a model produces a candidate, what independent mechanism decides whether the candidate is allowed to affect accepted state?

### B. Runtime governance and verification

AgentGuard and Dogwood demonstrate the growing importance of observing and constraining agent behavior at runtime. These systems strengthen the case that agent reliability is partly a control-plane problem. Residual extends this framing to a full acceptance pipeline in which tool authority, evidence, semantic verification, provenance, and deterministic integration are separate stages.

### C. Formal verification and proof-carrying systems

Proof-Carrying Code and model checking provide the deeper systems analogy: an untrusted producer need not itself be trusted if a smaller trusted boundary can check a relevant property. Residual adopts this philosophy but uses heterogeneous domain verifiers, not a claim of universal formal proof. A receipt is an integrity/provenance artifact; semantic authority remains with the verifier.

### D. Fault-tolerant and distributed systems

Classic fault-tolerant computing motivates the central hypothesis that component failures do not necessarily imply system failure. The analogy must be used carefully: Residual currently controls task acceptance and integration, but it should not imply consensus guarantees or Byzantine fault tolerance that are not implemented.

## References to verify in final IEEE bibliography

- L. Chen, M. Zaharia, and J. Zou, “FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance,” arXiv:2305.05176, 2023.
- I. Ong et al., “RouteLLM: Learning to Route LLMs with Preference Data,” arXiv:2406.18665, 2024; revised 2025.
- A. Shafran, R. Schuster, T. Ristenpart, and V. Shmatikov, “Rerouting LLM Routers,” arXiv:2501.01818, 2025.
- T. Feng et al., “LLMRouter: Unified Infrastructure for Developing, Evaluating, and Deploying LLM Routers,” arXiv:2608.06867, 2026.
- R. Koohestani, “AgentGuard: Runtime Verification of AI Agents,” arXiv:2509.23864, 2025.
- M. Brooker, J. Tassarotti, and J.-B. Tristan, “Introducing Dogwood: runtime verification for AI agents,” AWS Open Source Blog, Aug. 2026. Treat as engineering prior art, not peer-reviewed literature.
- G. C. Necula, “Proof-Carrying Code,” POPL, 1997.
- L. Lamport, R. Shostak, and M. Pease, “The Byzantine Generals Problem,” ACM TOPLAS, 1982.
- E. M. Clarke, O. Grumberg, and D. A. Peled, *Model Checking*, 1999.
- C. Baier and J.-P. Katoen, *Principles of Model Checking*, 2008.

Before submission, verify venue, pages, DOI, author ordering, and final publication status from primary sources rather than copying this working bibliography verbatim.
