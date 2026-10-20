# Evidence-Bounded Recursive Software Maintenance

## A Controlled and Protected Self-Hosting Study in RESIDUAL

**Mike Olivares — RESIDUAL Project**  
New Haven, Connecticut, USA  
*Preprint research manuscript; not peer reviewed*

> Repository-readable companion to the IEEE preprint **Evidence-Bounded Recursive Software Maintenance: A Controlled and Protected Self-Hosting Study in RESIDUAL**. The canonical rendered PDF used for this study has SHA-256 `e57445ed55f27afd9cbb39ee4c2be094a2798ed4b142c92ae2b860f3509a50f6`.

## Abstract

Recent software-engineering agents can modify repositories and resolve nontrivial issue descriptions, while decades of autonomic-computing and automatic-program-repair work have established feedback control and machine-generated repair as feasible mechanisms. A harder problem appears when the software being modified is the maintenance system itself: the candidate producer may become entangled with the authority that defines success, grants capabilities, verifies evidence, or promotes the result.

This paper investigates **evidence-bounded recursive software maintenance (EBRSM)**, in which software may build, document, verify, and repair candidate versions of itself without acquiring unilateral authority to approve those candidates. We analyze and experimentally probe the RESIDUAL Agent Harness at exact repository states. Controlled experiments establish fail-closed verification, bounded authority, spoof resistance, provenance-bound artifacts, bounded repair, documentation-policy dependence, and durable replay.

We then execute a protected self-hosting trial against a real open RESIDUAL research deficiency. A live GPT-5.6 Sol interactive worker generated a four-file candidate implementing frozen research-evidence bundles. RESIDUAL reconstructed that candidate on the frozen base, ran visible and hidden acceptance, evaluated it with three distinct same-process acceptance predicates, and classified it `PR_READY` while retaining **no merge authority**. The candidate touched zero protected trust-boundary paths. Exact-head repository qualification passed across Python 3.11–3.13, Docker, browser/UI, control-plane, ownership, clean-install, measured-evaluation, and generated WebVM browser-proof gates.

A deterministic 100-generation controller-lineage stress preserved a valid receipt chain with zero merge-authorized generations. Across 1,000 synthetic controller fault-injection trials, we observed zero false accepts and zero false rejects. Across 200 synthetic documentation-policy cases, required stale documentation and `UNKNOWN` documentation evidence produced zero false accepts, while a negative control confirmed that stale documentation remains acceptable when freshness is outside the frozen contract.

These results strengthen the case that recursive maintenance can be operationally bounded by evidence and external authorization. They do **not** establish internally provider-backed autonomous generation, arbitrary repair correctness, semantic-documentation intelligence, independent trust-domain review, or safe unattended production promotion.

## 1. Introduction

Software maintenance is increasingly executable by machines. Automatic program repair can synthesize patches from tests or other oracles, and modern language-model agents can inspect repositories, edit multiple files, run tools, and propose coordinated changes. In parallel, autonomic-computing and self-adaptive-software research has long treated software operation as a feedback problem: observe the system and environment, reason over goals, select an adaptation, execute it, and continue observing.

Those lines of work suggest an apparent next step: software that continuously builds, documents, heals, and verifies itself. Recursive maintenance, however, creates a trust problem that does not arise when the maintainer and maintained system are cleanly separated. If a candidate can change its own success criteria, verifier, budget accounting, capability grants, or promotion mechanism, then a run may appear successful precisely because the candidate changed the meaning of success.

The central research question is therefore not merely whether an AI can edit its own source code. It is whether recursive software maintenance can preserve an **external, inspectable basis** for deciding that a candidate should be accepted.

RESIDUAL approaches that problem by separating construction from authority. The governing invariant is:

> **A system may construct a candidate of itself, but the candidate may not unilaterally enlarge or approve the authority used to accept that candidate.**

This study makes six contributions:

1. It defines a system model that separates recursive construction from authorization.
2. It maps self-building, self-documenting, self-healing, and self-verifying behavior onto explicit control-plane mechanisms.
3. It evaluates those mechanisms against exact repository states rather than relying only on architectural argument.
4. It uses negative controls to distinguish demonstrated behavior from broader product claims.
5. It executes a protected self-hosting trial in which a live model proposes a real RESIDUAL repository repair that is reconstructed on a frozen base, hidden-tested, and promoted only to a draft pull request with merge authority remaining external.
6. It adds deterministic lineage, fault-injection, and documentation-policy stress campaigns while explicitly distinguishing those simulations from repeated live-model generations.

## 2. Background and Related Work

### 2.1 Autonomic and self-adaptive software

Autonomic-computing research frames complex systems as feedback-controlled software that can monitor, analyze, plan, and execute adaptations under high-level goals. Architecture-based self-adaptation systems such as Rainbow demonstrated reusable infrastructure for this loop. EBRSM inherits the feedback-loop intuition but changes the controlled object: recursive maintenance permits changes to source code and potentially to the maintenance system itself.

That produces a second-order control problem. The mechanism performing the adaptation can become part of the adaptation target. The goal, authority, verification, and promotion semantics must therefore remain outside the candidate's unilateral control.

### 2.2 Automatic program repair and software agents

Automatic program repair established that software can synthesize fixes from tests, contracts, models, crashes, and runtime state. The central limitation is the quality of the oracle. A plausible patch can satisfy available tests while remaining semantically wrong.

Repository-scale language-model agents extend the repair surface. Benchmarks such as SWE-bench demonstrate the difficulty of real coordinated repository changes, while agent-interface research shows that the computer/tool interface materially changes performance. These systems primarily ask whether an agent can solve a software task. EBRSM asks a different question: **what must remain externally trustworthy when the repository being changed contains the agent harness and its own maintenance controls?**

### 2.3 Self-documentation and drift

Documentation maintenance is a long-standing software-engineering problem. For recursive maintenance we distinguish three levels:

- **D1 — evidence documentation:** automatically emit receipts, manifests, handoffs, and change records.
- **D2 — change-coupled documentation:** update documentation artifacts as part of an accepted change.
- **D3 — semantic documentation synchronization:** detect and correct arbitrary semantic drift between code and prose.

The present work demonstrates D1 and bounded instances of D2. It does not establish D3.

### 2.4 Trust and provenance

Recursive construction also intersects with software supply-chain trust. Source inspection alone does not establish trust in the mechanism that produced an executable. Proof-carrying-code and provenance systems separate an untrusted producer from an independent checker or downstream consumer. EBRSM applies the same general principle to agentic maintenance: **generation is not acceptance**.

## 3. System Model

Let `S_t` be the software state at maintenance epoch `t`, `G_t` an immutable goal and acceptance contract, `C_t` the capabilities granted for the current mission revision, and `O_t` the observations available to the builder.

A builder produces a candidate and evidence claims:

`(S'_t, E'_t) = B(S_t, G_t, C_t, O_t)`

A host-side verifier evaluates the candidate against the frozen contract:

`V(S'_t, G_t, E'_t) ∈ {PASS, FAIL, UNKNOWN}`

Promotion is separate:

`S_(t+1) = P(S'_t)` only when verification passes and the authority policy permits the transition.

`UNKNOWN` is never coerced to `PASS`. Missing evidence therefore blocks automatic acceptance.

Within a mission revision, the executable capability set must remain no more permissive than the frozen grant. A candidate that needs new authority must create a revision request rather than silently reinterpret the current mission.

### 3.1 Four target capabilities

**Self-building** means the system can construct a candidate version of its own code or surrounding artifacts within an authorized workspace. It does not imply permission to merge that candidate into a protected branch.

**Self-verifying** means acceptance is computed from verifier-controlled evidence rather than worker claims. Worker prose such as “pass” or “complete” is never authoritative.

**Self-documenting** means maintenance events can emit receipts, handoff artifacts, evidence manifests, and bounded change-coupled documentation.

**Self-healing** means a failed or interrupted maintenance attempt can be diagnosed, repaired within bounded authority, replayed, and recovered without silently widening the mission.

## 4. Research Questions

The study centers on the following questions:

- **RQ1 — Authority:** Can recursive maintenance construct a candidate without obtaining merge, branch-protection, trust-boundary, or self-approval authority?
- **RQ2 — Verification:** Do `FAIL`, `UNKNOWN`, verifier exceptions, missing predicates, forged proposer identity, or scope escape remain non-accepting?
- **RQ3 — Evidence:** Can retained artifacts bind results to exact source bytes and expose tampering?
- **RQ4 — Repair:** Can rejected work be repaired while preserving bounded generation and receipt lineage?
- **RQ5 — Documentation:** Does documentation freshness become enforceable only when it is part of the frozen acceptance contract?
- **RQ6 — Recovery:** Can durable state and evidence replay survive interruption without silently changing the acceptance semantics?
- **RQ7 — Protected self-hosting:** Can a live model-authored repair to RESIDUAL itself reach a PR-ready state while merge authority remains external?

## 5. Experimental Design

### 5.1 Frozen states

The common frozen base for the protected self-hosting study is:

`22a5bae54ec12987ffd7a90d881fb4533c9b4b97`

The final hardened experimental head is:

`9624d66d7d0746f45f425361036eeacdc6358640`

The later commit that adds this repository-readable paper is documentation publication only; it is **not** substituted for the frozen experimental head.

### 5.2 Candidate scope

The live external interactive model worker authored exactly four candidate files:

- `residual/research_bundle.py`
- `scripts/research_bundle.py`
- `tests/test_research_bundle.py`
- `docs/research/RESEARCH_BUNDLES.md`

The isolated reconstructed candidate commit on the frozen base is:

`1afb8ef145fcd4e9a0d948f126e48248ae1b97d2`

The candidate feature freezes exact research-artifact bytes, extracts declared metrics through JSON Pointer, binds every metric to its source artifact SHA-256 and pointer, renders manuscript-ready tables, and verifies clean-checkout reproduction without model credentials.

### 5.3 Protected authority boundary

The self-maintenance controller allows only a closed safe action set:

- `file.write`
- `git.commit`
- `pull_request.create`

It rejects merge authority, main-branch push authority, branch-protection writes, trust-boundary writes, policy-authority writes, and self-approval. It also rejects canonical-path violations, Windows/backslash traversal spellings, `.git` metadata, and protected repository surfaces including `.github/`, the control plane, Factory, verifier, GoalSpec, and loop-control files.

### 5.4 Acceptance

The protected candidate is evaluated by three distinct acceptance predicates:

1. scope and authority,
2. behavioral/hidden acceptance,
3. documentation structure.

These predicates execute inside one controller process. They are separate checks but **not independent trust-domain reviewers**.

The hidden behavioral check runs the new research-bundle CLI end-to-end, freezes source-bound metrics, verifies the bundle, mutates a retained source artifact, and requires verification to reject the mutation.

## 6. Results

### 6.1 Focused self-maintenance qualification

The final hardened exact head passed **26/26** focused self-maintenance and evidence-bundle tests.

The live candidate was classified `PR_READY` with:

- merge authority: **false**,
- protected candidate paths touched: **0**,
- visible candidate feature tests: **6/6 passed**,
- hidden freeze/verify/tamper acceptance: **passed**,
- mutated frozen source artifact: **rejected**.

### 6.2 Long-horizon controller-lineage stress

A deterministic synthetic controller campaign executed **100 linked generations**. The receipt chain remained valid and **0 generations** acquired merge authority.

This experiment stresses lineage and authority invariants. It is **not** evidence of 100 live model-authored recursive code-generation cycles.

### 6.3 Synthetic controller fault injection

A deterministic campaign ran **1,000 trials** across forbidden authority, write-scope escape, `UNKNOWN`, explicit predicate failure, predicate exception, missing predicate, and forged proposer identity.

Observed results:

- false accepts: **0**,
- false rejects: **0**.

These are policy/runtime stress cases, not 1,000 live autonomous self-modification attempts.

### 6.4 Synthetic documentation-policy simulation

A **200-case** documentation-policy campaign tested stale documentation, explicit freshness requirements, unavailable evidence, and a negative control where documentation freshness was outside the contract.

Observed results:

- required-stale false accepts: **0**,
- `UNKNOWN` accepts: **0**,
- negative-control stale documentation remained acceptable when freshness was outside the frozen contract.

The result supports a narrow conclusion: documentation freshness can be enforced when explicitly specified. It does not establish general semantic documentation understanding.

### 6.5 Ordinary exact-head repository qualification

The final hardened experimental head passed:

- protected self-hosting workflow,
- Controller/provider contracts on Python 3.11, 3.12, and 3.13,
- Command Station on Python 3.11, 3.12, and 3.13,
- Station Docker smoke,
- Station browser/UI checks,
- Control Plane,
- Factory ownership gate,
- measured-evaluation acceptance binding,
- clean-install qualification,
- Pages artifact build and validation,
- generated WebVM artifact proof in desktop Chromium,
- generated WebVM artifact proof in a narrow/mobile Chromium viewport.

## 7. Protected Self-Hosting Outcome

The trial targeted open research issue #35: unify retained experiment artifacts and derive manuscript metrics/tables from exact source-bound evidence in a clean checkout.

The workflow's GitHub token had read-only repository-content authority. It could execute the experiment and retain evidence but could not publish the candidate, merge it, modify branch protection, or approve itself.

An external publication step opened **draft PR #132**. The PR remains unmerged by design. This preserves the experiment's primary authority boundary: candidate construction and qualification can be automated, but promotion still requires an external authorized decision.

The strongest supported conclusion is therefore:

> **Recursive software maintenance can construct and publish a qualified successor of the maintenance system itself while keeping authorization to promote that successor outside the candidate.**

## 8. Claim Boundaries

The study does **not** establish:

- internally provider-backed autonomous issue selection and generation,
- repeated live-model recursive self-improvement across 100 generations,
- independent external trust-domain qualification by the three internal predicates,
- general repair correctness across arbitrary repositories and defect classes,
- semantic documentation-drift understanding,
- production infrastructure self-healing,
- safe unattended merge or production promotion.

These are intentionally left as future experimental thresholds rather than being inferred from mechanism-level evidence.

## 9. Threats to Validity

**Single live candidate.** The protected self-hosting result contains one live external-model-authored candidate. It establishes feasibility, not a distribution over arbitrary maintenance problems.

**Same-process acceptance predicates.** The three acceptance predicates are distinct checks but share one process and are not independent reviewer identities or trust domains.

**Synthetic stress campaigns.** The 100-generation, 1,000-fault, and 200-documentation campaigns exercise controller semantics using deterministic fixtures. They should not be generalized to repeated live model evolution.

**Oracle quality.** Hidden acceptance and repository CI reduce risk but do not prove semantic correctness beyond the encoded checks.

**Environment.** The exact results bind to the recorded repository revisions, workflow environments, and retained artifacts. Generalization to other hosts and provider configurations requires further study.

## 10. Next Experiments

### 10.1 Independent adversarial verification

Move candidate generation and acceptance into genuinely distinct trust domains, with independent actor identities and evidence transport.

### 10.2 Semantic documentation benchmark

Construct code/document pairs containing renamed parameters, changed defaults, removed APIs, stale examples, misleading diagrams, changed failure modes, and plausible but false prose. Measure drift-detection precision/recall and repair correctness.

### 10.3 Real-code long-horizon recursive evolution

Run 50–100 real code-maintenance candidates under a fixed external policy root with periodic clean-checkout requalification. Measure cumulative regression, architecture complexity, verifier drift, documentation accuracy, cost, and human-intervention rate.

### 10.4 Infrastructure fault injection

Inject process termination, network partitions, provider timeouts, disk-full conditions, corrupted caches, delayed acknowledgements, stale leases, duplicate messages, and partial writes while verifying evidence continuity and bounded recovery.

### 10.5 Internally provider-backed autonomous self-hosting

Have RESIDUAL itself detect a bounded deficiency, select a configured provider or local model through its own routing layer, generate the candidate, run hidden qualification, and reach the same PR-ready boundary without a human composing the patch. The system must still lack merge/approval authority.

## 11. Reproducibility and Artifact Record

### Original proof-of-mechanism study

- branch: `research/self-maintenance-study-20260915`
- final supplemented workflow: `35044189082`
- commit: `cac91abe34fa16670de71a77acfffeadd6642d6a`
- retained artifact ID: `10426338141`

### Protected self-hosting study

- branch: `research/protected-self-hosting-trial-20260915`
- frozen base: `22a5bae54ec12987ffd7a90d881fb4533c9b4b97`
- final hardened experimental head: `9624d66d7d0746f45f425361036eeacdc6358640`
- isolated live candidate: `1afb8ef145fcd4e9a0d948f126e48248ae1b97d2`
- dedicated workflow run: `35045986860`
- evidence artifact ID: `10427205992`
- evidence artifact SHA-256: `09b627315255ea19f5be767634315929c5763f07d59eddbb8df3807ef6f41b31`
- Pages proof artifact ID: `10427111755`
- Pages proof SHA-256: `d5bd8de1b822e8300db20e21094557053ab2a696022b2f3aee98391270bfbc89`
- canonical IEEE PDF SHA-256: `e57445ed55f27afd9cbb39ee4c2be094a2798ed4b142c92ae2b860f3509a50f6`
- draft publication boundary: PR #132

See also [`../research/PROTECTED_SELF_HOSTING_TRIAL.md`](../research/PROTECTED_SELF_HOSTING_TRIAL.md) and [`../research/RESEARCH_BUNDLES.md`](../research/RESEARCH_BUNDLES.md).

## 12. Conclusion

The initial controlled study established necessary mechanisms for evidence-bounded maintenance: revision-bounded authority, explicit non-accepting uncertainty, host-controlled verification/accounting, bounded repair, provenance-bound artifacts, tamper detection, documentation-policy dependence, and durable recovery.

The protected self-hosting extension moves one step beyond proof of mechanism. A live interactive model produced a real four-file RESIDUAL candidate for an existing research deficiency. RESIDUAL reconstructed it on the frozen base, subjected it to scope, hidden-behavior, and documentation gates, and classified it PR-ready while retaining zero merge authority. The exact head then passed the repository's multi-version, Docker, browser, control-plane, ownership, clean-install, measured-evaluation, and generated WebVM browser qualification.

The evidence supports a stronger but still bounded conclusion: **recursive software maintenance can construct and publish a qualified successor of the maintenance system itself while keeping authorization to promote that successor outside the candidate**.

What remains unproven is equally important: internally provider-backed autonomous generation, general repair correctness, semantic documentation understanding, real-code long-horizon evolution, independent trust-domain verification, and production fault tolerance. Those are the next scientific thresholds—not reasons to weaken the current authority boundary.

## References

1. J. O. Kephart and D. M. Chess, “The vision of autonomic computing,” *Computer*, vol. 36, no. 1, pp. 41–50, 2003. DOI: 10.1109/MC.2003.1160055.
2. D. Garlan, S.-W. Cheng, A.-C. Huang, B. Schmerl, and P. Steenkiste, “Rainbow: Architecture-based self-adaptation with reusable infrastructure,” *Computer*, vol. 37, no. 10, pp. 46–54, 2004. DOI: 10.1109/MC.2004.175.
3. M. Salehie and L. Tahvildari, “Self-adaptive software: Landscape and research challenges,” *ACM Transactions on Autonomous and Adaptive Systems*, vol. 4, no. 2, 2009. DOI: 10.1145/1516533.1516538.
4. W. Weimer, T. Nguyen, C. Le Goues, and S. Forrest, “Automatically finding patches using genetic programming,” ICSE, 2009. DOI: 10.1109/ICSE.2009.5070536.
5. M. Monperrus, “Automatic software repair: A bibliography,” *ACM Computing Surveys*, vol. 51, no. 1, 2018. DOI: 10.1145/3105906.
6. H. Ye, M. Martinez, T. Durieux, and M. Monperrus, “A comprehensive study of automatic program repair on the QuixBugs benchmark,” *Journal of Systems and Software*, vol. 171, 2021. DOI: 10.1016/j.jss.2020.110825.
7. C. E. Jimenez et al., “SWE-bench: Can language models resolve real-world GitHub issues?” ICLR, 2024.
8. J. Yang et al., “SWE-agent: Agent-computer interfaces enable automated software engineering,” arXiv:2405.15793, 2024.
9. J. Yang et al., “SWE-smith: Scaling data for SWE-agents,” NeurIPS, 2025, arXiv:2504.21798.
10. I. Badertdinov et al., “SWE-rebench: An automated pipeline for task collection and decontaminated evaluation of software engineering agents,” NeurIPS, 2025.
11. L. Cai, Y. Ren, Y. Zhang, and J. Li, “AI-driven self-evolving software: A promising path toward software automation,” arXiv:2510.00591, 2025.
12. M. Robol and P. Giorgini, “Self-evolving software agents,” arXiv:2604.27264, 2026.
13. T. C. Lethbridge, J. Singer, and A. Forward, “How software engineers use documentation: The state of the practice,” *IEEE Software*, vol. 20, no. 6, pp. 35–39, 2003. DOI: 10.1109/MS.2003.1241364.
14. B. Dagenais and M. P. Robillard, “Using traceability links to recommend adaptive changes for documentation evolution,” *IEEE Transactions on Software Engineering*, vol. 40, no. 11, pp. 1126–1146, 2014. DOI: 10.1109/TSE.2014.2347969.
15. K. Thompson, “Reflections on trusting trust,” *Communications of the ACM*, vol. 27, no. 8, pp. 761–763, 1984. DOI: 10.1145/358198.358210.
16. G. C. Necula, “Proof-carrying code,” POPL, 1997. DOI: 10.1145/263699.263712.
17. S. Torres-Arias, H. Afzali, T. K. Kuppusamy, R. Curtmola, and J. Cappos, “in-toto: Providing farm-to-table guarantees for bits and bytes,” USENIX Security, 2019.
18. C. E. Anchundia and E. R. Fonseca C., “Resources for reproducibility of experiments in empirical software engineering,” *IEEE Access*, vol. 8, pp. 8992–9004, 2020. DOI: 10.1109/ACCESS.2020.2964587.
19. M. Olivares, “RESIDUAL Agent Harness,” GitHub repository, 2026.
