# Recursive Improvement Without Recursive Authority

## An Evidence-Governed Architecture for Self-Improving Agentic Software Systems

**RESIDUAL Research Paper — M6 Recursive Improvement Laboratory**  
**Status:** Design, experimental protocol, and empirical results through M6-SPEC-006  
**Experiment date:** 2026-09-18

## Abstract

Agentic software systems can inspect repositories, modify code, execute tests, and coordinate specialized workers. This makes bounded recursive software engineering possible. The harder problem is preserving an independent basis for deciding whether a self-generated modification is actually an improvement.

This paper proposes **Recursive Improvement Without Recursive Authority (RIRA)**. A trusted RESIDUAL baseline may receive or formulate an improvement hypothesis, generate successor candidates, and experimentally evaluate them, while candidates remain unable to modify the protected evaluator, M4 authority boundary, qualification policy, evidence mechanism, or promotion authority.

The first self-hosting experiment, **M6-SPEC-001**, asked RESIDUAL to implement the initial ImprovementSpec contract using a real local Qwen2.5-Coder 1.5B model. The first authoritative run did **not** produce an acceptable candidate. RESIDUAL detected an incomplete first implementation, attempted repair, rejected a syntactically invalid second candidate, detected truncation on the third generation, and escalated after its maximum-iteration brake. No candidate was reviewed, integrated, exported, or promoted.

The initial experiment supported a narrower claim than successful recursive improvement: **RESIDUAL can govern and reject unsuccessful attempts to implement a component of its own proposed recursive-improvement architecture while retaining bounded execution and evidence.** Subsequent experiments M6-SPEC-002 through M6-SPEC-006 iteratively corrected repair context, transport/source ambiguity, attempt-limit inconsistency, and runtime provenance. M6-SPEC-006 then completed the frozen ImprovementSpec task end to end: two incorrect candidates were rejected, a third passed unchanged deterministic checks, independent review approved the exact head, integration issued a verification receipt, and release export succeeded. This demonstrates bounded recursive development for the tested task/configuration, not general autonomous recursive self-improvement or self-promotion.

## 1. Central Principle

> **RESIDUAL may propose its successor. It may not appoint its successor.**

Generation, evaluation, and promotion are distinct authority domains.

A candidate is untrusted until independently qualified. Candidate code MUST NOT be able to rewrite the authoritative evaluator, weaken protected acceptance criteria, suppress authoritative evidence, or promote itself.

## 2. Improvement Contract

RIRA introduces an ImprovementSpec containing an observation, falsifiable hypothesis, target metrics, metrics that must be preserved, protected invariants, acceptance criteria, and an explicit external-approval requirement. Improvement is therefore not represented by an unconstrained instruction such as "make yourself better."

The intended progression is:

1. **M6.0 — Recursive Evaluation:** evaluate manually specified changes.
2. **M6.1 — Recursive Development:** RESIDUAL implements a human-supplied ImprovementSpec.
3. **M6.2 — Improvement Discovery:** RESIDUAL proposes ImprovementSpecs from operational evidence.
4. **M6.3 — Closed-Loop Research:** RESIDUAL discovers, implements, evaluates, and presents a candidate while external authority retains promotion.

## 3. Evaluation Model

The currently trusted implementation is the **Champion** and generated implementations are **Challengers**. Evaluation is multi-dimensional rather than a single self-improvement score. Relevant dimensions include correctness, task success, latency, token/resource cost, determinism, evidence completeness, recovery behavior, and protected-invariant violations.

## 4. Experiment M6-SPEC-001

### 4.1 Research question

Can RESIDUAL use its own Station execution path and a real local coding model to implement one bounded component intended for RESIDUAL's recursive-improvement architecture, while the harness independently enforces behavioral checks and refuses unsuccessful candidates?

### 4.2 Frozen conditions

- Repository: ninja-ops-guy/residual-agent-harness
- Baseline: 699e2869e294fe157b4bfd73a272057683a2f7e0
- Experiment PR: #203
- Branch: experiment/m6-improvementspec-self-host
- Apparatus head: e123b90d012973bfd260ae5b955eebd4dbac48f0
- GitHub Actions run: 35305550407
- Python: 3.12
- Provider: Ollama
- Model: qwen2.5-coder:1.5b
- Workers: 1
- Model output ceiling: 1600 tokens
- Batch token budget: 30,000
- Batch wall-clock budget: 600 s
- Effective run-control maximum: 3 passes
- Specification SHA-256: dad4015272c4d990cb6fad4409042517c2ab5afa03ca82247bdc6d3ca244b6eb

The generated candidate was isolated from main. The task prohibited network, subprocess, filesystem, provider, Git, verifier, M4, receipt, and promotion operations inside the target module.

### 4.3 Target specification

The model was instructed to create residual/improvement/spec.py containing a frozen ImprovementSpec dataclass with identity, observation, hypothesis, target and preserved metrics, protected invariants, acceptance criteria, mandatory human approval, negative-path validation, deterministic canonical JSON, and deterministic SHA-256 identity.

Success required candidate generation, Python compilation, behavioral and negative-path checks, model-review approval, isolated integration, a verification receipt, and release export containing the generated source.

### 4.4 Observed execution

The first authoritative execution made three provider calls and consumed 5,526 reported tokens: 3,656 input and 1,870 output tokens. No cloud-model tokens were used. The mission ran for 125.374 seconds.

**Pass 1:** the generated file compiled, but the behavioral test could not import ImprovementSpec. One of two checks passed. RESIDUAL transitioned the task to repair_required.

**Pass 2:** the repair candidate contained an unclosed parenthesis at line 23. Both compilation and behavioral checks failed. RESIDUAL again transitioned to repair_required.

**Pass 3:** generation reached the configured 1,600-output-token ceiling. RESIDUAL recorded: "Model output was truncated. Narrow the task or increase the output limit." The maximum-iteration brake tripped at three passes.

| Measurement | Result |
|---|---|
| Candidate accepted | No |
| Integrated tasks | 0 / 1 |
| Final task state | repair_required |
| Passes | 3 |
| Provider calls | 3 |
| Reported tokens | 5,526 |
| Wall clock | 125.374 s |
| Model review | Not reached |
| Verification receipt | Not issued |
| Release export | Not produced |
| Run outcome | Escalated |
| Brake | max_iteration |

### 4.5 Result

**M6-SPEC-001 failed its primary success criterion.**

This must not be reported as successful self-improvement or successful self-hosted implementation.

The negative result nevertheless demonstrates several control properties in this run: generated source was not trusted merely because a model produced it; a compiling but behaviorally incomplete implementation was rejected; a syntactically invalid repair was rejected; truncated output was explicitly classified; repeated failure caused bounded escalation; no failed candidate reached review, integration, receipt issuance, export, or promotion; and evidence was retained after failure.

The result is evidence for **governed failure containment**, not yet for successful recursive development.

### 4.6 Failure analysis

The immediate failure was model/output-path related rather than evidence that the behavioral specification was unsatisfiable. The 1.5B model first produced an incomplete interface, then an invalid repair, and finally exhausted the configured 1,600-token output ceiling.

The experiment also exposed a configuration interaction: although the apparatus requested batch_max_passes=5, authoritative run control escalated at three passes. Reproduction must record actual run-control evidence rather than assuming the requested setting became effective.

A separate Ollama startup log reported port 11434 already bound. The health probe succeeded and three calls were recorded against the intended local model, so execution continued, but future replication should explicitly guarantee provider-process ownership.

## 5. Interpretation

**Can RESIDUAL yet reliably implement this M6 component with this model/configuration?** No. One trial cannot estimate reliability, and the first trial failed.

**Did the harness preserve its control boundary when implementation failed?** In this run, yes: checks rejected bad candidates, iteration remained bounded, the task escalated, and no failed artifact crossed the integration boundary.

This distinction is central to RIRA. A failed generation that is correctly detected and retained is preferable to an apparently successful experiment produced by weakened evaluation.

## 6. Repeatable Validation Procedure

### 6.1 Exact apparatus reproduction

Run:

~~~bash
git clone https://github.com/ninja-ops-guy/residual-agent-harness.git
cd residual-agent-harness
git fetch origin pull/203/head:m6-spec-001
git checkout e123b90d012973bfd260ae5b955eebd4dbac48f0
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[factory]'
~~~

Install Ollama using its official installation method, ensure one intended server owns 127.0.0.1:11434, and obtain the model:

~~~bash
ollama pull qwen2.5-coder:1.5b
curl -fsS http://127.0.0.1:11434/api/tags
~~~

Execute:

~~~bash
python scripts/m6_improvementspec_experiment.py \
  --model qwen2.5-coder:1.5b \
  --base-url http://127.0.0.1:11434 \
  --output runs/m6-improvementspec/evidence.json
~~~

The command intentionally exits non-zero when acceptance fails. Preserve evidence.json regardless of exit status.

### 6.2 Evidence validation

Record:

~~~bash
git rev-parse HEAD
sha256sum scripts/m6_improvementspec_experiment.py
python -m json.tool runs/m6-improvementspec/evidence.json >/dev/null
cat runs/m6-improvementspec/evidence.json
~~~

Validate these identifiers:

- baseline_sha = 699e2869e294fe157b4bfd73a272057683a2f7e0
- experiment = M6-SPEC-001
- spec_sha256 = dad4015272c4d990cb6fad4409042517c2ab5afa03ca82247bdc6d3ca244b6eb
- provider kind = ollama
- model = qwen2.5-coder:1.5b

A replication need not produce byte-identical model output unless inference determinism is separately demonstrated. Compare protocol and acceptance outcomes while retaining generated-source hashes for every trial.

### 6.3 Historical evidence

Original GitHub Actions run: 35305550407  
Job: 105476895809  
Artifact: m6-improvementspec-research-evidence  
Artifact ID: 10531533856  
Artifact ZIP SHA-256: 9002f40ead356585e98390be26c499174318abcaeb755fe0c56438bc169ad77f

The experiment PR is research apparatus and is intentionally not for merge.

### 6.4 Independent replication protocol

1. Use a fresh Linux environment.
2. Check out the exact apparatus commit.
3. Record Python, Ollama, and model versions/digests where available.
4. Ensure exactly one intended Ollama server owns the configured port.
5. Run without editing specification or checks.
6. Preserve evidence.json even on failure.
7. Record environment metadata, wall clock, provider calls, token counts, candidate hashes, checks, transitions, and final brake/outcome.
8. Never replace a failed trial with a retry. Number every execution.
9. Use a preregistered number of trials; at least 10 is recommended for the next study.
10. Report every trial, including truncations and infrastructure failures.

### 6.5 Successful-trial acceptance

A future trial qualifies only when all of these hold:

~~~text
batch.integrated == 1
task.state == "integrated"
all behavioral checks == PASS
review.approved == true
verification_receipt != null
generated_source != null
export_error == null
~~~

Independent inspection must also confirm that the candidate changed only the allowed target and did not alter protected evaluation or authority mechanisms.

## 7. Threats to Validity

**Single trial.** This experiment cannot estimate success probability.

**Model size.** Qwen2.5-Coder 1.5B is lightweight; its failure does not establish that stronger models would fail.

**Inference reproducibility.** Output can vary across model/runtime/hardware versions.

**Output ceiling.** The third generation hit the configured 1,600-token ceiling.

**Effective-pass mismatch.** Requested and effective pass limits differed and should be bound explicitly in future studies.

**Provider-process ambiguity.** The workflow observed an already-bound Ollama port. Future runs should prove process identity.

**Downstream gates untested.** Review, receipt, and export were not reached for this task.

## 8. Next Experiment

M6-SPEC-002 should be a preregistered replication, not a rewritten history of M6-SPEC-001. Keep the behavioral specification and acceptance tests frozen while varying exactly one controlled independent variable, such as model capability or output ceiling.

The primary endpoint should be complete accepted-implementation rate. Secondary endpoints should include first-pass correctness, repairs per success, tokens, wall time, truncation rate, and correctly contained failures.

## 9. Conclusion

M6-SPEC-001 did not demonstrate successful recursive software improvement. It demonstrated something preliminary but necessary: when RESIDUAL attempted to implement a component intended for its own recursive-improvement architecture and the model repeatedly produced unacceptable candidates, the harness rejected them, bounded the attempt, escalated, and retained evidence.

> **Models provide intelligence. They do not get authority.**

The next milestone is to reproduce the experiment, isolate the limiting variable, achieve a qualifying candidate under frozen acceptance criteria, and then demonstrate champion–challenger evaluation before any successor is eligible for external promotion.


# 10. Empirical Progression: M6-SPEC-002 through M6-SPEC-006

The later M6 experiments were numbered and retained independently. Failed trials were not replaced by reruns.

## 10.1 M6-SPEC-002 — Stronger Model Replication

M6-SPEC-002 replaced the 1.5B implementation model with Qwen2.5-Coder 7B while retaining the frozen ImprovementSpec task and three-pass control boundary.

The trial still failed closed. Across three attempts the candidate moved through successively narrower defects: an invalid `dataclasses.frozen` import, a missing `json` import, and missing whitespace-only identity validation. This indicated that increased model capability alone did not resolve the repair-process limitation.

The run consumed 5,336 reported tokens over 432.543 seconds and integrated no candidate.

## 10.2 M6-SPEC-003 — Prior-Candidate Repair Context

Failure analysis showed that `repair_required` preserved findings but did not provide the previous failed candidate's writable file contents. Repair therefore behaved closer to regeneration than correction.

M6-SPEC-003 added bounded `prior_candidate_files` while retaining a clean baseline worktree for every new attempt. Repair-context file hashes were recorded as evidence.

The trial still failed with the 1.5B model, but richer retained patches exposed a distinct failure mode: the model confused the outer structured JSON transport envelope with the contents of the target Python file.

This result demonstrated that repair context was necessary but not sufficient for the smaller model.

## 10.3 M6-SPEC-004 — Transport/Source Disambiguation

The runner contract was amended to state explicitly that the outer JSON object was transport only and that values for `.py` paths must contain literal Python source.

The representation failure disappeared: the agent began producing real Python implementations. The trial nevertheless failed within the then-effective three-pass envelope, repeatedly retaining an invalid `dataclasses.frozen` import.

This result isolated another system inconsistency: Store allowed five task attempts while Mission Control dispatched only three and capped a single-task GoalSpec at three passes.

## 10.4 M6-SPEC-005 — Integrated Remediation, Invalid Runtime Trial

The repair-context, transport/source, and shared-attempt-ceiling changes were combined and validated by deterministic regression tests. The integrated 7B validation trial then failed before candidate generation because a 4,096-token output ceiling caused the first local inference call to reach the Ollama adapter's 300-second timeout. Usage was unavailable, and RESIDUAL's fail-closed budget brake aborted the run.

This was classified as an infrastructure/configuration failure rather than a candidate-quality result.

## 10.5 M6-SPEC-006 — Successful Bounded Self-Hosting

M6-SPEC-006 retained the remediated harness but corrected runtime conditions:

- Qwen2.5-Coder 7B;
- dedicated Ollama endpoint;
- 1,600-token output ceiling;
- five-attempt bounded repair envelope;
- 1,800-second mission wall-clock budget;
- unchanged ImprovementSpec behavioral checks;
- unchanged review, receipt, integration, M4, and promotion authority boundaries.

The result was successful.

### Repair trajectory

**Attempt 1:** Candidate compiled but imported nonexistent `frozen` from `dataclasses`. Behavioral verification rejected it.

**Attempt 2:** Prior candidate was hash-bound into repair context. The invalid import was removed, but the candidate accepted a whitespace-only `improvement_id`. Behavioral verification rejected it.

**Attempt 3:** The second candidate was bound into repair context. The model corrected string validation using `.strip()`. Both frozen checks passed.

Only after deterministic acceptance did RESIDUAL invoke review. The local reviewer approved the exact checked head with no findings. RESIDUAL then re-ran integration checks, integrated the exact reviewed revision, issued a station verification receipt, and exported the generated source.

### Measurements

| Measurement | M6-SPEC-006 |
|---|---:|
| Outcome | success |
| Attempts | 3 |
| Integrated | 1 / 1 |
| Frozen checks | 2 / 2 |
| Provider calls | 4 |
| Reported tokens | 9,217 |
| Input tokens | 7,521 |
| Output tokens | 1,696 |
| Mission wall clock | 759.722 s |
| Reviewer | approved |
| Verification receipt | issued |
| Release export | successful |
| False acceptance observed | 0 |

Generated source SHA-256:

`90aaf5b4d35f6eaff11a0c4a85cf3c2764c0255407cca95c6c1e352cca30edbf`

Verification receipt hash:

`0c45802590a839a101cfb08dbb000fe34540365dee9cd790083419d1ccac6a0e`

Retained experiment artifact SHA-256:

`ab7d8cfb639557510fff9789aa4c14a2ed940ecc71b37a5190fba0de84f13e61`

## 10.6 Lessons Supported by the Series

The M6-001..006 sequence supports several engineering conclusions for the tested environment:

1. **Repair context matters.** Corrective attempts should receive the exact prior candidate plus exact failure evidence, while beginning from a clean worktree.
2. **Transport semantics matter.** Structured response envelopes must be explicitly distinguished from the language/content expected inside writable files.
3. **Bounded retries must have one authority.** Contradictory attempt ceilings create hidden behavior and invalidate experiment assumptions.
4. **Failure evidence should survive temporary execution environments.** Per-attempt patches, checks, usage, transitions, and receipts materially improved diagnosis.
5. **Runtime provenance is part of validity.** Model identity, endpoint ownership, output ceiling, and timeout budget can determine whether an experiment tests the model/harness at all.
6. **Review should remain downstream of deterministic verification.** No failed candidate in this series obtained reviewer or integration authority.
7. **Improved capability should not weaken acceptance.** The successful trial used the same frozen behavioral checks that rejected prior attempts.

# 11. Transition to M6.2 — Autonomous Improvement Discovery

M6-SPEC-006 establishes a bounded recursive-development path for one tested task: RESIDUAL can implement a component for itself, consume its own failure evidence, repair candidates, pass unchanged external checks, obtain independent review, integrate the exact reviewed head, issue a receipt, and export source.

The next research question moves the starting point backward:

> Can RESIDUAL derive a falsifiable ImprovementSpec from hash-bound measurements of its own behavior, rather than receiving the engineering hypothesis from a human?

M6.2 therefore introduces:

- a first-class `ImprovementSpec`;
- content-addressed `EvidenceSnapshot`;
- an analysis-only Improvement Scientist;
- a mechanical hypothesis verifier;
- an append-only experiment ledger;
- champion/challenger evaluation;
- an external promotion boundary.

The planned M6-SPEC-007 experiment will provide RESIDUAL with a hash-bound evidence snapshot and require the Improvement Scientist to originate one measurable, falsifiable improvement hypothesis before any implementation is authorized.

The central authority invariant remains unchanged:

> **RESIDUAL may discover, propose, implement, and evaluate a successor candidate. It may not redefine the protected evaluator or appoint the successor.**
