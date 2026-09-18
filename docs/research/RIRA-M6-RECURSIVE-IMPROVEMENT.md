# Recursive Improvement Without Recursive Authority

## An Evidence-Governed Architecture for Self-Improving Agentic Software Systems

**RESIDUAL Research Paper — M6 Recursive Improvement Laboratory**  
**Status:** Design, experimental protocol, and first empirical result  
**Experiment date:** 2026-09-18

## Abstract

Agentic software systems can inspect repositories, modify code, execute tests, and coordinate specialized workers. This makes bounded recursive software engineering possible. The harder problem is preserving an independent basis for deciding whether a self-generated modification is actually an improvement.

This paper proposes **Recursive Improvement Without Recursive Authority (RIRA)**. A trusted RESIDUAL baseline may receive or formulate an improvement hypothesis, generate successor candidates, and experimentally evaluate them, while candidates remain unable to modify the protected evaluator, M4 authority boundary, qualification policy, evidence mechanism, or promotion authority.

The first self-hosting experiment, **M6-SPEC-001**, asked RESIDUAL to implement the initial ImprovementSpec contract using a real local Qwen2.5-Coder 1.5B model. The first authoritative run did **not** produce an acceptable candidate. RESIDUAL detected an incomplete first implementation, attempted repair, rejected a syntactically invalid second candidate, detected truncation on the third generation, and escalated after its maximum-iteration brake. No candidate was reviewed, integrated, exported, or promoted.

The experiment therefore supports a narrower claim than successful recursive improvement: **RESIDUAL can govern and reject unsuccessful attempts to implement a component of its own proposed recursive-improvement architecture while retaining bounded execution and evidence.** A successful self-hosting result remains to be demonstrated.

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
