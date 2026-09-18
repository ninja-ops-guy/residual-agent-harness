# Recursive Improvement Without Recursive Authority

## An Evidence-Governed Architecture for Self-Improving Agentic Software Systems

**RESIDUAL Research Paper — M6 Recursive Improvement Laboratory**  
**Status:** Design, empirical program through M6-SPEC-006, and M6.2 discovery protocol  
**Experiment date:** 2026-09-18

## Abstract

Agentic software systems can inspect repositories, modify code, execute tests, and coordinate specialized workers. This makes bounded recursive software engineering possible. The harder problem is preserving an independent basis for deciding whether a self-generated modification is actually an improvement.

This paper proposes **Recursive Improvement Without Recursive Authority (RIRA)**. A trusted RESIDUAL baseline may receive or formulate an improvement hypothesis, generate successor candidates, and experimentally evaluate them, while candidates remain unable to modify the protected evaluator, M4 authority boundary, qualification policy, evidence mechanism, or promotion authority.

The M6 experimental program progressed from governed failure containment to successful bounded recursive development. M6-SPEC-001 through M6-SPEC-005 exposed repair-context loss, transport/source ambiguity, inconsistent attempt limits, provider-process ambiguity, and runtime-budget interactions. Those failures were preserved as authoritative evidence and converted into harness changes without weakening acceptance or promotion authority.

**M6-SPEC-006 subsequently succeeded.** Using a real local Qwen2.5-Coder 7B model, RESIDUAL rejected two incorrect candidates, supplied hash-bound prior-candidate context to later repair attempts, accepted the third only after unchanged deterministic checks passed, obtained independent review approval, integrated the exact reviewed head, issued a verification receipt, and exported the generated source.

The current claim is therefore: **RESIDUAL has demonstrated bounded recursive development under external evaluation and promotion authority.** The next research question is whether it can originate a defensible improvement objective from its own evidence rather than merely execute a human-supplied hypothesis.

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


## 10. Experimental Progression: M6-SPEC-002 through M6-SPEC-006

The failed trials after M6-SPEC-001 were not discarded. Each isolated a different weakness in the development loop.

### M6-SPEC-002 — stronger model, unchanged repair semantics

Qwen2.5-Coder 7B still failed within three passes. The failure sequence was informative rather than random: an invalid dataclasses import was followed by a missing json import and then incomplete blank-string validation. This suggested that the model could make progressively narrower corrections but was not being given the prior candidate as explicit repair context.

### M6-SPEC-003 — prior-candidate repair context

RESIDUAL supplied the prior writable files as bounded repair context while still constructing each new attempt from a clean baseline worktree. The 1.5B model still failed, but retained patches exposed a new representation error: it confused the outer structured JSON transport with the literal contents required inside a Python source file.

### M6-SPEC-004 — transport/source disambiguation

The runner contract explicitly separated the transport envelope from file-language content. The model stopped emitting data objects into Python files and began producing real Python source. It still failed within the three-pass ceiling, revealing an inconsistency: Store permitted five task attempts while Mission Control stopped dispatching after three.

### M6-SPEC-005 — integrated remediation, invalid runtime configuration

The repaired harness was tested with the recommended 7B coding model, but a 4096-token output ceiling caused the first Ollama request to hit the adapter's 300-second transport timeout. Unknown usage correctly tripped the fail-closed budget brake. This trial is classified as an infrastructure/configuration abort, not a model-quality failure.

### M6-SPEC-006 — corrected runtime, successful bounded self-hosting

# M6-SPEC-006 — Successful Post-Remediation Validation

## Result

M6-SPEC-006 is the first successful bounded RESIDUAL self-hosting experiment in the M6 series.

The experiment used the unchanged ImprovementSpec behavioral specification from M6-SPEC-001 and the remediated harness derived from failures in M6-SPEC-001 through M6-SPEC-005.

### Frozen runtime
- harness: `e7488199ee238f04ef1547338199096389047b2e`
- model: `qwen2.5-coder:7b`
- model ID: `dae161e27b0e`
- provider: Ollama 0.34.2
- dedicated endpoint: `127.0.0.1:11437`
- max output: 1600 tokens
- batch max passes: 5
- mission wall-clock budget: 1800 s
- no cloud fallback

### Outcome
- batch outcome: **success**
- attempts: **3**
- integrated: **1 / 1**
- frozen checks: **2 / 2 passed**
- reviewer: **approved**
- verification receipt: **issued**
- release export: **successful**
- generated source: **present**
- false acceptance observed: **0**
- provider calls: **4** (3 runner + 1 reviewer)
- reported tokens: **9,217**
- input tokens: **7,521**
- output tokens: **1,696**
- request bytes: **32,721**
- mission wall clock: **759.722 s**
- generated source SHA-256: `90aaf5b4d35f6eaff11a0c4a85cf3c2764c0255407cca95c6c1e352cca30edbf`
- verification receipt hash: `0c45802590a839a101cfb08dbb000fe34540365dee9cd790083419d1ccac6a0e`

Research artifact:
- name: `m6-spec-006-corrected-runtime-evidence`
- artifact ID: `10543236401`
- artifact ZIP SHA-256: `ab7d8cfb639557510fff9789aa4c14a2ed940ecc71b37a5190fba0de84f13e61`
- Actions run: `35334715201`

## Repair trajectory

### Attempt 1
The model produced a nearly complete Python implementation but incorrectly imported `frozen` from `dataclasses`.

Mechanical compilation passed because imports are not resolved by AST compilation. The behavioral command correctly failed during import.

RESIDUAL rejected the candidate and entered `repair_required`.

### Attempt 2
The previous candidate was hash-bound into the repair context. The model removed the invalid `frozen` import.

The candidate then failed a deeper negative-path condition: whitespace-only `improvement_id` was accepted.

RESIDUAL rejected the candidate and retained the new checks/patch evidence.

### Attempt 3
The second candidate was hash-bound into the next repair request. The model changed string validation to use `.strip()` for identity, observation, hypothesis, metrics, and protected invariants.

Both frozen checks passed.

RESIDUAL then:
1. transitioned the candidate to local_verified;
2. submitted it for independent model review;
3. received an approved review with no findings;
4. transitioned it to approved;
5. integrated the exact reviewed head;
6. emitted integration-check evidence;
7. issued a station verification receipt;
8. exported the accepted release;
9. retained the generated source and its SHA-256.



The result matters because no acceptance rule was relaxed between the failed and successful experiments. The system improved by carrying better corrective context, clarifying the output contract, aligning bounded attempt semantics, and controlling runtime provenance.

## 11. Evidence Dimensionality and Measurement-Gap Discovery

Improvement discovery is bounded not only by model reasoning but by the dimensions represented in the evidence.

A Scientist that can reason perfectly over an incomplete EvidenceSnapshot can still discover only deficiencies visible through the measured axes. This creates a second-order discovery problem: the system may need to determine that **the evidence is insufficient to decide whether an improvement opportunity exists**.

RIRA therefore distinguishes two legitimate Scientist outputs:

1. **ImprovementSpec** — a falsifiable hypothesis grounded in existing measured evidence.
2. **MeasurementGap** — a bounded proposal explaining which evidence dimension is missing, why it is required, and how it could be collected mechanically.

A MeasurementGap is not a defect claim. Missing telemetry cannot be transformed into evidence that a problem exists. Instead, it records:

- the unanswered question;
- the absent metric;
- the evidence snapshot that lacks it;
- the proposed measurement method;
- protected invariants that instrumentation must preserve;
- the external approval requirement for changing observability.

This prevents a common failure mode in autonomous research systems: inventing confidence where the evidence schema is silent.

The recursive research loop therefore becomes:

```text
EvidenceSnapshot
      |
      +--> sufficient dimensions --> ImprovementSpec
      |
      +--> insufficient dimensions --> MeasurementGap
                                      |
                                approved instrumentation
                                      |
                               new measured evidence
                                      |
                                 EvidenceSnapshot'
```

The evidence schema itself can thus evolve through explicit, auditable proposals without allowing the Scientist to silently redefine what counts as evidence.

## 12. M6.2 — From Recursive Development to Improvement Discovery

M6-SPEC-006 closes the bounded development loop. M6.2 moves the starting point backward.

The target sequence is:

```text
trusted run evidence
        ↓
EvidenceSnapshot
        ↓
Improvement Scientist
        ↓
ImprovementSpec OR MeasurementGap
        ↓
mechanical hypothesis verification
        ↓
external experiment authorization
        ↓
bounded candidate development
        ↓
champion/challenger evaluation
        ↓
review + receipt
        ↓
external promotion gate
```

The Scientist is intentionally analysis-only. Denying source-write and promotion authority is not merely a safety restriction; it forces the Scientist's contribution to remain legible as an argument that can be independently falsified.

The central M6.2 question is therefore not whether a model can suggest something that sounds useful. It is whether RESIDUAL can originate an improvement hypothesis that is:

- grounded in hash-bound measurements;
- nontrivial rather than a restatement of an existing task;
- falsifiable under a preregistered experiment;
- explicit about preserved metrics and protected invariants;
- mechanically rejected when it relies on unmeasured claims;
- converted into a MeasurementGap when the available evidence is insufficient.

M6-SPEC-007 is reserved for this discovery test.

## 13. Updated Conclusion

The experimental program has moved beyond the original M6-SPEC-001 result.

RESIDUAL has now demonstrated a bounded form of recursive development: it can use a real model to implement software intended for its own architecture, reject incorrect versions, repair from retained evidence, pass an unchanged external standard, obtain independent review, integrate the exact reviewed candidate, issue a verification receipt, and export the result.

That does **not** establish autonomous recursive improvement.

The remaining distinction is epistemic: who originates the improvement objective?

M6.2 tests whether RESIDUAL can move from executing a supplied ImprovementSpec to constructing a defensible one from its own measured history—or explicitly conclude that a required evidence dimension is missing.

The authority invariant remains unchanged:

> **RESIDUAL may discover, propose, implement, and evaluate a successor. It may not appoint that successor.**


## 14. M6-EPI-001 — Evidence Sufficiency vs. Measurement Gap

M6-EPI-001 tested the evidence-dimensionality concern directly using two controlled EvidenceSnapshots.

The sufficient arm contained `repair_attempts_mean = 2.4`, `task_success_rate = 0.72`, and `verification_failures = 14`. The insufficient arm deliberately omitted `repair_attempts_mean` while retaining a question that required it.

Both tasks initially failed their semantic checks and succeeded after one bounded repair. The final batch integrated 2/2 tasks in two passes, using six local model calls and 7,417 reported tokens over 499.011 seconds.

The sufficient arm produced an improvement proposal bound to the exact snapshot hash and used the measured baseline value 2.4. The insufficient arm produced a MeasurementGap identifying exactly `repair_attempts_mean` as absent and did **not** fabricate a numeric baseline, hypothesis, or acceptance criterion.

This supports the feasibility of the epistemic fork:

```text
required dimension measured  -> candidate ImprovementSpec
required dimension absent    -> MeasurementGap
```

However, the experiment also demonstrated why the Scientist cannot validate its own output. The sufficient proposal expressed acceptance as free-form prose and confused a preservation metric with a protected invariant. The MeasurementGap left its preserve-invariants set empty. Those outputs passed the intentionally narrow experimental checks but are not acceptable production contracts.

The production HypothesisVerifier specification was therefore strengthened to require structured mechanically evaluable acceptance criteria, a versioned invariant vocabulary, non-empty MeasurementGap preservation invariants, and exact EvidenceSnapshot binding.

Evidence artifact SHA-256: `ed9b1f790039629d2d9dd5bd52f0ef37cd505835e1c08f3ff6094e574fa49008`.

## 15. M6-SHIP-001 — First Real-Repository Roadmap Shipping Attempt

M6-SHIP-001 moved beyond the empty experimental repository. RESIDUAL imported a clean clone of the actual repository and was assigned the first M6.2 roadmap deliverable: implement the production `residual/improvement/spec.py` contract while receiving read-only context from existing core code.

The attempt failed closed after all five bounded repair attempts.

The generated module was close to correct. It validated blank fields, serialized tuple fields as lists, defensively copied the acceptance mapping, and was frozen. Its critical defect was:

```python
def canonical_json(self) -> bytes:
    return canonical(self.to_dict()).encode()
```

The contract required `canonical_json()` to return text. The behavioral check correctly rejected the candidate.

The more important process finding was that the check used a bare assertion. The retained diagnostic was only an `AssertionError` line number. Attempts 2 through 5 received the same prior candidate plus the same opaque finding and reproduced the exact same candidate patch hash:

`1cf89833ff7a6c2d8bfeb6f5b9f2c1d1ec402082427b475f4911d39882a88881`

The system did not falsely accept the candidate, but it spent the full repair budget without changing state.

M6-SHIP-001 therefore produced two new engineering requirements:

1. **Repair evidence quality matters.** Deterministic checks intended to drive automated repair should emit explicit expected/actual diagnostics rather than bare assertions.
2. **Stagnation should be classified.** Repeated identical candidate+failure states should become deterministic repeated-failure evidence rather than consuming every remaining attempt as though progress occurred.

Issue #235 tracks repeated-candidate stagnation detection.

M6-SHIP-002 preserves the same roadmap contract and acceptance semantics while changing only the diagnostic quality of the deterministic test. This tests whether precise failure evidence is sufficient to convert the stagnant loop into corrective repair.

## 16. Updated Research Implication

The M6 program now exposes three distinct requirements for autonomous recursive improvement:

- **development competence:** the system can modify and repair code;
- **epistemic competence:** the system can distinguish measured evidence from missing evidence;
- **experimental competence:** the evaluator provides diagnostics rich enough to drive correction and detects when the repair process is no longer making progress.

A recursive system that lacks any one of these can remain bounded and safe yet fail to improve effectively.

The emerging closed loop is therefore:

```text
measure
  ↓
detect sufficiency or MeasurementGap
  ↓
form falsifiable hypothesis
  ↓
implement candidate
  ↓
verify with actionable evidence
  ↓
repair while progress exists
  ↓
classify stagnation if progress stops
  ↓
review + receipt
  ↓
champion/challenger comparison
  ↓
external promotion
```


## 17. Experimental Competence: Lessons from M6-SHIP-002 and M6-SHIP-003

The attempt to ship a real roadmap task exposed failures in the experimental apparatus itself.

### M6-SHIP-002 — verifier representation failure

M6-SHIP-002 converted opaque bare assertions into explicit expected/actual diagnostics. However, placing the full verifier inside a `python -c` command exceeded Station's existing 2,000-character argv-element contract. The mission was rejected during specification parsing before any model call occurred.

This is not a model failure.

The resulting rule is:

> Nontrivial acceptance logic should be represented as an immutable versioned verifier artifact, invoked by a short command.

This improves auditability, reuse, provenance, and repair diagnostics while avoiding command-envelope limits.

### M6-SHIP-003 — context-cost failure

M6-SHIP-003 adopted an external verifier, but supplied that verifier together with broad read-only context from `residual/core.py` and `residual/goalspec.py`.

The resulting runner request was 32,652 bytes. The Qwen2.5-Coder 7B call reached the Ollama adapter's 300-second timeout before returning a candidate or usage. The fail-closed budget brake then aborted because usage was unknown.

By contrast, successful M6-SPEC-006 requests were approximately 5.6–8.6 KB.

This is again not evidence that the implementation hypothesis was wrong. It is evidence that task-context selection can determine whether an experiment is executable.

Issue #240 therefore tracks pre-dispatch context-cost visibility and empirical model/context envelopes.

### Implication

A recursive improvement system requires an additional competence beyond hypothesis quality and coding ability:

**experimental competence** — the ability to distinguish candidate failure from invalid experimental conditions.

An autonomous research controller should classify at least:

- candidate rejected by deterministic evidence;
- hypothesis rejected mechanically;
- evidence insufficient;
- verifier/specification invalid;
- provider/runtime unavailable;
- context envelope impractical;
- repair stagnated;
- experiment completed.

Only the first categories constitute evidence about the proposed implementation or hypothesis itself.

M6-SHIP-004 tests the same roadmap task with the immutable external verifier but minimal read-only context.


## 18. M6-ROADMAP-001B — Shipping a Real Roadmap Task with RESIDUAL

A parallel roadmap experiment corrected an important methodological issue in the first productionization attempt: the source repository presented to RESIDUAL must be the exact intended baseline, not a workflow branch that also contains the experimental apparatus.

M6-ROADMAP-001B therefore materialized a detached clean copy of:

`main@260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`

and gave that source tree to the production RESIDUAL harness. The write scope was restricted to the new M6 package files.

### Result

The experiment succeeded in one implementation attempt.

- implementation checks: **3 / 3 passed**
- model review: **approved**
- integration: **completed**
- verification receipt: **issued**
- release export: **completed**
- implementation attempts: **1**
- provider calls: **2** (runner + reviewer)
- reported tokens: **4,384**
- mission wall clock: **435.182 s**
- candidate false acceptance observed: **0**

The exact generated files were:

`residual/improvement/__init__.py`  
SHA-256: `3981e064c31f85763e872c47129975a61cc8d6ab8e00f1851d216eeb269ba623`

`residual/improvement/spec.py`  
SHA-256: `0bdcb3b7f86aad5d684f7437df88f3342055bbc08a9df6b51cbe859656ca7616`

Station verification receipt hash:

`880fbacee5fdfb13aded09e2297c14d7006f4da2c208ac292f8283a936199695`

Retained evidence artifact:

- artifact ID: `10546904820`
- artifact ZIP SHA-256: `908b3b748b7d4841bdf92330e2cee5708bc65547663788dd5d0de29a4477effc`
- Actions run: `35347061630`

### Independent production-test provenance

To avoid allowing the generated implementation to define its own production acceptance surface, the production contract tests were authored separately before the successful generated source was inspected and copied into the shipping branch.

The generated source is promoted to production byte-for-byte. The production PR therefore creates a provenance chain:

```text
independently authored tests
        +
exact-main RESIDUAL experiment
        ↓
generated source hashes
        ↓
review + verification receipt
        ↓
exact-byte production copy
        ↓
normal repository CI / clean-install qualification
```

Production PR #243 contains this exact generated source plus those independent tests.

### Research significance

This is stronger than the earlier empty-workspace self-host experiment.

M6-ROADMAP-001B demonstrates that RESIDUAL can operate against a clean snapshot of its **actual repository**, produce a bounded change for its own M6 architecture, pass external deterministic checks and review, and export an artifact that can be promoted unchanged through the project's ordinary software-delivery process.

It still does not demonstrate autonomous improvement discovery; the roadmap task and contract were supplied externally.

## 19. Shipping-Process Lessons

The series of real-repository shipping attempts produced several process lessons that matter for autonomous improvement:

1. **Pin the source baseline explicitly.** Experimental workflow files must not silently become implementation context.
2. **Keep implementation context minimal and task-relevant.** Broad repository context increases latency and may cause provider timeout without improving task quality.
3. **Represent substantial verification as immutable artifacts.** Large inline command strings are hard to audit and can exceed mission-contract bounds.
4. **Verification diagnostics are part of the repair channel.** A correct but opaque rejection can produce repeated identical repairs.
5. **Repeated identical candidate+failure states are not progress.** Station should classify stagnation rather than consume the full bounded attempt budget.
6. **Separate experiment validity from candidate validity.** Provider timeout, manifest rejection, or context-budget failure must not be counted as evidence against an implementation hypothesis.
7. **Promote exact accepted bytes.** Once RESIDUAL has produced a reviewed and receipted artifact, productionization should preserve its identity rather than silently hand-editing the candidate.

Together, these results suggest that autonomous recursive improvement requires not only coding and hypothesis generation, but a trustworthy experiment-operations layer capable of preserving provenance and classifying failure modes correctly.


## 20. M6-SHIP-004 — Minimal-Context Shipping Replication

M6-SHIP-004 repeated the real-repository ImprovementSpec task with the immutable external verifier but removed unrelated read-only source files from model context.

The first runner request shrank from 32,652 bytes in M6-SHIP-003 to 7,663 bytes. The Qwen2.5-Coder 7B call completed in 275.152 seconds instead of timing out at the 300-second adapter boundary.

The full mission ultimately succeeded after five bounded passes.

- outcome: **success**
- implementation attempts: **5**
- model calls: **6** (5 runner + 1 reviewer)
- reported tokens: **16,558**
- input tokens: **14,005**
- output tokens: **2,553**
- mission wall clock: **1,163.466 s**
- review: **approved**
- receipt hash: `b6e678480c9cdbfa802696bb977849bdef139ccf005142d661de824e56e31e7c`
- release export: **successful**
- generated source SHA-256: `6556120bc6c370b198b16dc964745ae0dcb05d0b4328f39e3aadcfd77ec39fec`
- evidence artifact SHA-256: `7a6b9b31c9ca7116a73ea49ea9ba85c71a7ecd24097942e86af9b0aaf70ced69`

### Repair sequence

1. Candidate used an invalid `dataclasses.frozen` import.
2. A repair response failed write-scope validation rather than producing a usable replacement.
3. The invalid `frozen` import persisted.
4. The dataclass construction was corrected, but required `json`/hash imports were missing.
5. The missing imports were added and the unchanged verifier passed.

This experiment demonstrates two separate properties.

First, context minimization can be the difference between an executable local-model experiment and a transport timeout.

Second, repair efficiency remains stochastic and imperfect even when sufficient evidence is available. The successful exact-main replication M6-ROADMAP-001B completed the same roadmap contract in a single implementation attempt, while M6-SHIP-004 required the entire five-attempt envelope.

Therefore context minimization should be treated as an execution-reliability requirement, not as a guarantee of reasoning quality.

The production artifact continues to use the cleaner exact-main M6-ROADMAP-001B provenance rather than substituting the later five-attempt candidate merely because it also passed.


## 21. M6-SPEC-007 — First Autonomous Discovery Attempt

M6-SPEC-007 was the first trial in which RESIDUAL received measured M6 history without being given an improvement question, target metric, intervention, or hypothesis.

The model-visible EvidenceSnapshot contained both aggregate measurements and full per-run rows for five retained M6 development/shipping runs.

The first Scientist call timed out at the Ollama adapter's 300-second boundary before returning a proposal.

- request bytes: **15,566**
- passes: **1**
- proposal produced: **no**
- outcome: **aborted**
- brake: **usage_unknown_or_invalid**
- EvidenceSnapshot hash: `55bb8dfd86be33329ea145ee1a25e16feec65fe03fc69ef2f03b058c4a399e50`
- retained artifact SHA-256: `c322faeaa8e499a730b8038ff6da90c4de22785755d88356583da2ddae1bb3e7`

This result is classified as an **experiment-execution failure**, not an epistemic failure. No hypothesis or MeasurementGap was produced, so the trial provides no evidence about whether the Scientist can originate a defensible improvement objective.

The follow-up, M6-SPEC-007B, preserves the same aggregate measurements, provenance hashes, no-supplied-hypothesis condition, deterministic checker, review, receipt, and authority boundaries while removing verbose per-run rows from model-visible context.

This follows the experimental-competence rule established earlier: reduce unnecessary context before interpreting a provider timeout as a failure of reasoning.


## 22. M6-SPEC-007B — Compact Snapshot Still Exceeds Local Discovery Envelope

M6-SPEC-007B removed the verbose per-run rows from the Scientist's model-visible EvidenceSnapshot while preserving the exact aggregate measurements and source evidence hashes.

The first request shrank from 15,566 bytes to 12,927 bytes, but the local Qwen2.5-Coder 7B call still reached the Ollama adapter's 300-second timeout before producing a proposal.

- proposal produced: **no**
- request bytes: **12,927**
- elapsed: **300.093 s**
- outcome: **aborted**
- brake: **usage_unknown_or_invalid**
- compact snapshot hash: `7bbb1196ff3e96fb818a34941f0bebc5d35498ea1115656a475f21bfd043eb6a`
- evidence artifact SHA-256: `bb5ab558b3db4768d44553db2fb3a13f5922afedf0250ff40f8f40fa2b04e73b`

The result further isolates the execution problem. The Scientist was still given the full immutable verifier source as read-only context even though verifier implementation details are not required to originate a proposal.

M6-SPEC-007C therefore separates proposal generation from verifier implementation visibility. The model receives only the compact EvidenceSnapshot and a concise output contract. The same deterministic verifier remains external and authoritative.

This separation strengthens the architecture conceptually as well as operationally:

```text
Scientist sees:
  evidence + admissible output contract

Scientist does NOT see:
  verifier implementation as task context

Verifier sees:
  evidence + Scientist proposal

Verifier decides:
  admissible / rejected
```

The Scientist therefore cannot optimize against verifier implementation details while still being held to the same mechanically enforced contract.


## 23. M6-SPEC-007C — Autonomous Objective Selection Reached, Admission Failed at Representation

M6-SPEC-007C removed verifier implementation source from the Scientist's model-visible context. The first request fell to 6,878 bytes and completed in 187.339 seconds, allowing the experiment to reach the actual discovery question for the first time.

The Scientist independently selected:

- primary observed metric: `shipping_task_success_rate = 0.6`;
- comparison metric: `provider_timeout_rate = 0.2`;
- hypothesis: reducing provider timeouts should increase shipping-task success;
- target metric: `shipping_task_success_rate`;
- preservation metric: `provider_timeout_rate`;
- protected invariant: `M4`;
- evidence binding: exact compact EvidenceSnapshot hash;
- authority: human approval retained.

No improvement question, target metric, intervention, or hypothesis was supplied by the experiment.

This is evidence of **autonomous objective selection** within the bounded evidence scope.

The proposal did not pass formal admission. Attempts repeatedly malformed the JSON representation of the acceptance criterion:

```text
"operator">="
```

instead of a valid key/value pair. The deterministic JSON and proposal verifiers therefore rejected every candidate. Repeated-patch detection identified recurring failed proposals, and the final generation hit the 1,200-token output ceiling. The run escalated after five bounded passes.

- first request bytes: **6,878**
- calls: **5**
- reported tokens: **12,840**
- wall clock: **752.384 s**
- integrated proposal: **none**
- review reached: **no**
- false admission: **0**
- evidence artifact SHA-256: `50398a007fb67aee739d81b9b726ebf0d5caf0a45fac1599b74cc31ae40ff782`

### Interpretation

The experiment separates two capabilities that had previously been conflated:

1. **epistemic reasoning** — selecting a measured deficiency and forming a falsifiable improvement direction;
2. **representation compliance** — encoding that reasoning into the exact machine contract expected by the verifier.

M6-SPEC-007C provides positive evidence for the first capability and negative evidence for the second.

The appropriate remediation is not to weaken the verifier or manually repair the proposal. Instead, M6-SPEC-007D moves serialization out of the scientific task entirely:

```text
EvidenceSnapshot
      ↓
Scientist returns typed structured object
      ↓
RESIDUAL canonical serializer
      ↓
deterministic external HypothesisVerifier
      ↓
independent reviewer
      ↓
admission receipt
```

The model will no longer be asked to hand-author JSON source text. The scientific question therefore becomes whether the structured proposal is admissible, rather than whether the model can place punctuation correctly.

This is the precise boundary between observed autonomous discovery and formally admitted autonomous discovery.


## 24. M6-SPEC-007D — Typed Representation Solves Serialization, Exposes Epistemic Error

M6-SPEC-007D removed hand-authored JSON source from the Scientist task. The model returned a typed object under a response schema; RESIDUAL then serialized the object canonically and applied the same deterministic admission semantics.

The representation layer succeeded immediately:

- request bytes: **3,755**
- input tokens: **700**
- output tokens: **209**
- Scientist elapsed time: **95.275 s**
- structured response parse: **successful**
- canonical serialization: **successful**

The Scientist returned a `measurement_gap` bound to the exact EvidenceSnapshot hash and preserved all registered invariants.

However, the proposal claimed that `provider_timeout_rate` was missing even though the snapshot explicitly contained:

```text
provider_timeout_rate = 0.2
```

The deterministic verifier rejected the proposal with:

```text
missing_metric is not actually missing
```

No semantic reviewer was invoked and no admission receipt was issued.

### Interpretation

M6-SPEC-007D cleanly separates the representation problem from the epistemic problem.

The 007C failure was mostly interface-level: the underlying improvement direction was coherent but the model repeatedly malformed JSON punctuation.

The 007D failure is materially different. The model successfully expressed a typed proposal but misread the evidence state and asserted that a measured metric was absent.

This is precisely the class of error the M6.2 architecture is designed to catch mechanically.

The result supports three conclusions:

1. typed structured output is the correct representation boundary for the Scientist;
2. deterministic evidence admission remains necessary even when structured output is schema-valid;
3. a typed response schema cannot substitute for epistemic verification.

M6-SPEC-007E therefore keeps typed output and the same evidence, but adds bounded repair from deterministic verifier findings. A mechanically rejected proposal may be revised using the explicit admission error, while the verifier itself remains immutable.

The next stage remains blocked until a proposal is both mechanically admissible and independently semantically approved.


## 25. M6-SPEC-007E — Typed Repair Cannot Correct a Mechanically Known Epistemic Error

M6-SPEC-007E retained the typed representation from 007D and added a bounded three-attempt repair loop driven by deterministic verifier findings.

The first proposal again emitted a MeasurementGap for `provider_timeout_rate`, despite the EvidenceSnapshot measuring that metric at `0.2`.

The verifier returned an explicit correction:

```text
missing_metric 'provider_timeout_rate' is already measured at 0.2;
choose improvement_spec or a genuinely absent metric
```

The same finding was then included in attempts two and three together with the previous typed proposal.

All three attempts returned the exact same proposal.

- Scientist calls: **3**
- reported tokens: **3,112**
- proposal SHA-256 on every attempt:
  `1cccd1ac661b621a9a3b0e88b2220f1d34d44ea0768a37cbb652bfcd75c31268`
- mechanical admission: **failed**
- semantic review reached: **no**
- admission receipt: **none**
- evidence artifact SHA-256:
  `b705aabb937a361d13293d3d9d44c7c62258dd42bb9d809c54b0e1f0fb25554e`

### Interpretation

This result reveals an important distinction between **repairable reasoning** and **mechanically knowable constraints**.

The fact that `provider_timeout_rate` is already present in the EvidenceSnapshot does not require model reasoning. It is an exact machine-known property.

Asking the model to remember and obey that fact through free-text repair feedback wastes inference and permits repeated epistemic error.

The resulting design rule is:

> If a proposal property can be constrained directly from trusted evidence, encode that constraint into the structured response contract before generation and verify it again afterward.

M6-SPEC-007F therefore makes the Scientist schema evidence-aware:

- observation and declared target/preserve metric IDs are constrained to measured metric IDs;
- protected invariants are constrained to the registered invariant vocabulary;
- MeasurementGap is prevented from naming already-measured metric IDs where the structured-output implementation supports the constraint;
- deterministic post-generation verification remains authoritative.

The model still chooses the improvement objective. The system merely prevents structurally impossible claims from occupying the proposal space.


## 26. M6-SPEC-007F — Evidence-Aware Schema Does Not Replace Deterministic Verification

M6-SPEC-007F attempted to move mechanically known evidence constraints into the model response schema itself.

Measured metric IDs were used as enums for observation, target, preservation, and acceptance fields. Registered invariant IDs were likewise constrained. The MeasurementGap branch attempted to prevent already-measured metrics from appearing as `missing_metric` using a JSON Schema `not + enum` constraint.

The model still returned:

```text
type = measurement_gap
missing_metric = provider_timeout_rate
```

even though the EvidenceSnapshot measured:

```text
provider_timeout_rate = 0.2
```

The provider-side structured-output path therefore did not enforce the intended semantic exclusion.

The deterministic post-generation verifier rejected the proposal.

- Scientist call: **completed**
- request bytes: **5,667**
- elapsed: **89.804 s**
- reported tokens: **887**
- mechanical admission: **failed**
- semantic review reached: **no**
- false admission: **0**
- evidence artifact SHA-256:
  `e963dfcb8dab977557788332385b934feb354a95cd0d199f867a97b055903ab6`

### Implication

Structured decoding is useful for representation correctness, but provider implementations may support only a subset of JSON Schema semantics.

RIRA must therefore preserve the ordering:

```text
typed generation
      ↓
deterministic host verification
      ↓
semantic review
```

Provider-side schema enforcement is an optimization and interface aid, not a trust boundary.

The repeated MeasurementGap behavior also raises a model-role question. The Scientist experiments through 007F used `qwen2.5-coder:7b`, a model selected originally for implementation work rather than evidence analysis.

M6-SPEC-007G therefore changes only the analysis model role to general `qwen2.5:7b` while preserving the evidence, typed proposal contract, deterministic verifier, semantic reviewer, and human promotion boundary.


## 27. M6-SPEC-007H — First Mechanically Admissible Autonomous Discovery Proposal

M6-SPEC-007H separated a measured anomaly from the missing evidence needed to explain it.

The Scientist autonomously produced:

- observed metric: `context_bytes_non_success_mean`;
- observed value: **31,629.0**, exactly matching the EvidenceSnapshot;
- missing metric: `context_bytes_total_mean`, absent from the EvidenceSnapshot;
- question: whether the large non-success context mean reflects a real anomaly or incomplete baseline information;
- proposed measurement: collect total context-byte mean;
- protected invariants: M4, evidence integrity, verification integrity, and promotion authority;
- exact EvidenceSnapshot hash;
- human approval retained.

The deterministic verifier returned **zero mechanical errors**.

This is the first M6-SPEC-007-series proposal to cross mechanical evidence admission.

The independent semantic reviewer then rejected the proposal, and no admission receipt was issued.

### Reviewer-contract finding

The rejection is useful but reveals a semantic-review mismatch.

The reviewer demanded:

- evidence for a causal relationship;
- a falsifiable causal acceptance criterion;
- preservation criteria tied to a proposed intervention.

Those requirements are appropriate for an ImprovementSpec, but a MeasurementGap exists specifically because the evidence required to form such a causal hypothesis is not yet available.

A MeasurementGap should instead be reviewed for:

1. whether its observed anomaly is meaningful and exactly evidence-bound;
2. whether the requested measurement is genuinely absent and nonredundant;
3. whether the proposed measurement is mechanically collectible;
4. whether collecting it could resolve the stated uncertainty;
5. whether authority and integrity invariants remain protected.

M6-SPEC-007I therefore keeps the 007H Scientist contract and mechanical verifier but makes semantic review branch-aware.

### Metrics

- Scientist request: **4,327 bytes**
- Scientist tokens: **761 input / 280 output**
- Scientist elapsed: **111.416 s**
- reviewer tokens: **914 input / 111 output**
- reviewer elapsed: **90.253 s**
- mechanical admission: **PASS**
- semantic review: **REJECT**
- admission receipt: **none**
- evidence artifact SHA-256:
  `149c1f56e32d8f23df2f53b739bfafb4e4567138bf3e796c9831ffc2c9d9552f`

The retained evidence payload contains a stale internal `experiment: M6-SPEC-007D` label inherited from the base apparatus. The authoritative workflow, PR, evidence marker, script hash, and artifact identify the run as 007H. The stale field is retained as research evidence rather than rewritten; later apparatus corrects it prospectively.


## 28. M6-SPEC-007I and 007J — From Apparatus Failure to First Formally Admitted Autonomous Discovery

M6-SPEC-007I was intended to test branch-aware semantic review, but a stale task identifier remained in the experiment apparatus. The manifest created `m6-discover-007i` while the Scientist usage receipt attempted to bind to `m6-discover-007d`. Station rejected the mismatched identity with `ContractError: Task was not found`.

007I is therefore classified as an apparatus identity failure. It produced no usable experiment proposal and is not evidence about the Scientist or reviewer.

M6-SPEC-007J corrected the apparatus prospectively by defining one authoritative task identity and using it for the manifest, Scientist, reviewer, and receipt.

### Result

M6-SPEC-007J succeeded.

With no supplied improvement question, target metric, intervention, or hypothesis, the Scientist autonomously produced:

- observed metric: `context_bytes_non_success_mean`;
- observed value: **31,629.0**;
- missing metric: `context_bytes_non_success_max`;
- question: whether a particular failure scenario is driving the high average non-success context size;
- proposed measurement: collect the maximum non-success context size;
- protected invariants: M4, evidence integrity, verification integrity, and promotion authority;
- exact EvidenceSnapshot binding;
- human approval retained.

The deterministic verifier returned **zero errors**.

The independent branch-aware reviewer approved the proposal and found that:

- the anomaly was meaningful and evidence-bound;
- the missing measurement was genuinely absent and nonredundant;
- the proposed measurement was mechanically collectible;
- collecting it could materially resolve the uncertainty;
- the preserved authority/integrity invariants were appropriate.

RESIDUAL then issued admission receipt:

`09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`

Proposal SHA-256:

`3876881dc9dd662197217337c0b5ae7fd20f626e4221e82cfc24154437779d23`

Evidence artifact SHA-256:

`ea74dce1d0706a880566e694d872c76e305b8d28da0eee4dd89801e1232ad26e`

### Metrics

- Scientist: **761 input / 251 output tokens**
- Scientist request: **4,327 bytes**
- Scientist elapsed: **110.713 s**
- reviewer: **956 input / 108 output tokens**
- reviewer request: **3,475 bytes**
- reviewer elapsed: **97.896 s**
- total reported tokens: **2,076**

### Research significance

M6-SPEC-007J is the first experiment in the series to demonstrate the complete bounded discovery-admission path:

```text
retained self-development evidence
        ↓
Scientist selects an epistemic objective
        ↓
typed proposal
        ↓
deterministic evidence admission
        ↓
independent branch-aware semantic review
        ↓
cryptographic admission receipt
```

The admitted result is a MeasurementGap rather than an ImprovementSpec.

That distinction matters. The system did not force an intervention hypothesis from insufficient evidence. It concluded that one additional measurement was required first.

Therefore M6-008 remains blocked.

The correct next operation is evidence acquisition: collect `context_bytes_non_success_max` from the hash-bound retained source evidence, produce an enriched EvidenceSnapshot, and invoke the Scientist again. Only a subsequently admitted ImprovementSpec may advance to autonomous candidate implementation.


## 29. Closing the First Admitted Gap: M6-SPEC-007K through 007M

After 007J admitted `context_bytes_non_success_max` as a legitimate missing measurement, the next experiments tested whether RESIDUAL could acquire that evidence and continue discovery without forcing an intervention.

### 007K — apparatus failure

007K attempted to derive the admitted metric from retained non-success run records but referenced an incorrect local variable name. It failed before model execution and is classified as apparatus failure.

### 007L — admitted evidence acquired

007L corrected the apparatus and added an executable preflight.

The requested metric was derived from the bound retained runs:

- M6-SHIP-001: 30,606 first-request bytes;
- M6-SHIP-003: 32,652 first-request bytes.

Therefore:

`context_bytes_non_success_max = 32,652`

The enriched EvidenceSnapshot bound the derivation method, contributing run IDs, contributing artifact hashes, and originating 007J admission receipt.

The Scientist correctly observed the new maximum but then requested `context_bytes_non_success_mean` as missing even though the snapshot already measured it at 31,629.0. The deterministic verifier rejected the proposal before semantic review.

This demonstrated that closing a MeasurementGap does not guarantee that a small Scientist model will correctly track evidence availability.

### 007M — host EvidenceResolver

007M removed missingness authority from the Scientist.

The Scientist could emit either an ImprovementSpec or an EvidenceRequest. The trusted host then resolved the request:

```text
EvidenceRequest
   ↓
host EvidenceResolver
   ├─ present -> return exact trusted value and reassess
   └─ absent  -> host-classified MeasurementGap
```

Across three bounded calls the resolver returned:

1. `context_bytes_non_success_max = 32652`;
2. `context_bytes_non_success_mean = 31629.0`;
3. the second request repeated and was classified as stagnation.

No false MeasurementGap was created.

The experiment therefore succeeded at separating **evidence demand** from **evidence availability authority**, but the Scientist still failed to use already-resolved evidence reliably.

- Scientist calls: **3**
- reported tokens: **3,959**
- admission: **none**
- false missing-evidence classification: **0**
- evidence artifact SHA-256:
  `04ee76fd12e10d0d637311137453f3c1fef128c83d6620b566eb844fbd511f5b`

### Architectural implication

Passive inclusion of an EvidenceSnapshot in model context is not equivalent to evidence use.

The next design should make evidence inspection an explicit typed phase:

```text
metric catalog
      ↓
Scientist selects evidence to inspect
      ↓
host returns exact Evidence Bus/Snapshot values
      ↓
Scientist forms proposal or asks for a new measurement
      ↓
deterministic admission
      ↓
independent review
```

This preserves the Scientist's epistemic agency while keeping evidence truth and availability under deterministic host control.


## 30. Active Evidence Use and Role Decomposition: M6-SPEC-007N and 007O

### 007N — active evidence query

007N changed the Scientist from passive snapshot reading to explicit evidence selection.

Before seeing values, the Scientist selected:

- `shipping_task_success_rate`;
- `provider_timeout_rate`;
- `mean_wall_clock_s`;
- `successful_mean_wall_clock_s`.

The host returned exact values. The Scientist subsequently requested `mean_runner_attempts` and `mean_first_request_bytes`; the EvidenceResolver returned both. A later request repeated `mean_runner_attempts` and was classified as stagnation.

No false MeasurementGap was emitted.

The experiment showed that active evidence selection improves focus but does not by itself solve a mode-selection problem: a combined `ImprovementSpec | EvidenceRequest` Scientist can repeatedly choose the lower-commitment evidence-request branch.

A provenance-display defect was also found: the initial active-evidence history stored a mutable dictionary reference, so later resolver additions appeared retroactively in that history object. The separate evidence-query record preserved the original selected IDs. Later apparatus copies evidence snapshots before recording them.

### 007O — split Hypothesis Scientist and Measurement Planner

007O separated hypothesis formation from measurement planning.

The Evidence Scout first selected five metrics, including success rate, timeout rate, wall-clock metrics, and repeated-failure count.

The Hypothesis Scientist then returned `insufficient_evidence`, grounded in:

`mean_wall_clock_s = 696.4382`

It did not directly request a metric.

A separate Measurement Planner requested a baseline wall-clock measurement. The host classified the requested identifier as absent, the branch-aware reviewer approved the resulting MeasurementGap, and RESIDUAL issued receipt:

`674513d7e3b82c747bdbea408094ad2c08342943bb05a544e29a6d07727a5359`

The workflow therefore completed successfully.

### Post-hoc semantic audit

The successful workflow is not sufficient to establish semantic adequacy.

The requested metric identifier was:

`mean_wall_clock_s_basline`

The identifier is misspelled and its population/aggregation semantics are undefined. Moreover, the Scientist had already inspected:

`successful_mean_wall_clock_s = 786.123333`

which may overlap with the intended concept of a normal successful baseline.

The reviewer declared the requested measurement nonredundant without having a metric-definition registry capable of establishing that claim.

Accordingly, the 007O receipt remains integrity-valid for the recorded decision, but the research conclusion is downgraded to **UNKNOWN** under external audit.

This follows a core RESIDUAL distinction:

> receipt integrity and semantic adequacy are separate properties.

Issue #265 tracks the resulting requirement for a versioned discovery Metric Registry.

### Metric Registry requirement

A discovery metric must bind more than a name and value.

At minimum the registry should define:

- canonical metric ID;
- description;
- unit;
- aggregation semantics;
- observation population/unit;
- valid domain;
- directionality or interpretation;
- collection/implementation reference;
- revision/content hash.

New measurable axes should be proposed through a typed `MetricDefinitionProposal`, not an unconstrained string.

Exact duplicates can be rejected mechanically. Likely semantic overlap should be presented to independent review together with the existing metric definitions. Ambiguous metric semantics yield UNKNOWN.

This directly addresses the EvidenceSnapshot-dimensionality concern: recursive discovery requires a governed mechanism for expanding what the system can measure without silently creating duplicate, ambiguous, or incomparable dimensions.


## 31. Metric Identity Hardening: M6-SPEC-007P, 007R, and 007S

### 007P — deterministic Metric Registry controls

M6-SPEC-007P tested the Metric Registry against the exact semantic failure exposed by 007O.

All 16 focused Metric Registry unit tests passed.

Three preregistered controls then produced the expected classifications:

1. `mean_wall_clock_s_basline` with population `normal operating conditions`
   - result: **UNKNOWN**;
   - findings: ambiguous population plus likely semantic/spelling overlap;
   - similar registered metrics: `mean_wall_clock_s`, `successful_mean_wall_clock_s`.

2. a different metric ID with semantics identical to `mean_wall_clock_s`
   - result: **REJECT** as an exact semantic duplicate.

3. `first_call_elapsed_ms_mean` with explicit unit, aggregation, population, domain, collection method, implementation reference, and revision
   - result: **SEMANTIC_REVIEW**;
   - it was not automatically registered or admitted.

Registry revision:

`m6-discovery-v1`

Registry SHA-256:

`081f9bfa28c824650b701dbdf4b291f402442738497efc2144c1fe63b3431f5d`

Evidence artifact SHA-256:

`52fb43f4c842490d41ab7dc2c7e13393be6c3b5ad00efeae695ac2ac74af8303`

This closes the specific 007O false-positive class: string absence is no longer sufficient to establish a new measurable axis.

### 007R — exact provenance transcription failure

007Q was an apparatus failure before model execution due to a generated import serialization defect. 007R corrected that defect prospectively and passed syntax, registry tests, registry preflight, and model setup.

The Evidence Scout selected:

- `context_bytes_non_success_max`;
- `context_bytes_success_mean`;
- `identical_failure_repeats_total`;
- `shipping_task_success_rate`.

The Hypothesis Scientist then produced a substantively grounded `insufficient_evidence` proposal observing:

`context_bytes_non_success_max = 32652`

but copied the EvidenceSnapshot SHA-256 incorrectly as a 58-character value.

The deterministic verifier rejected the proposal with:

`evidence_snapshot_hash mismatch`

No Measurement Planner, reviewer, or admission receipt followed.

This is not a semantic-discovery failure. It exposes an unnecessary model responsibility: immutable provenance identity should not be transcribed by a probabilistic component.

The next architecture therefore moves EvidenceSnapshot identity, Metric Registry identity, and the retained human-gate flag into a deterministic host-authored envelope.

### 007S — registry semantics are receipt-bound

M6-SPEC-007S tested whether an old receipt could remain valid if metric semantics changed while the metric ID and human-readable registry revision string stayed the same.

The baseline registry hash was:

`081f9bfa28c824650b701dbdf4b291f402442738497efc2144c1fe63b3431f5d`

Changing the population and collection semantics of `mean_wall_clock_s` produced registry hash:

`38580fd26ad6dc5dd47eba4f53ec591fd39b27b78aa752393de4ea2b49750117`

All preregistered controls passed:

- baseline receipt matched original context;
- semantic change changed registry hash;
- semantic change changed admission cache-key binding;
- semantic change changed verifier-revision binding;
- old receipt failed context matching under altered semantics;
- direct EvidenceSnapshot registry-hash tampering was rejected;
- seconds/milliseconds unit mismatch was rejected.

Evidence artifact SHA-256:

`2a9a7e7a63c381e3b48577e2bfc393fc19c43be45a48f593f073e2e66f575ea1`

StationReceipt v2 itself was not modified.

The result establishes that discovery receipts can remain tied to metric semantics through existing receipt identities rather than weakening or expanding the protected receipt schema.


## 32. Host-Owned Provenance: M6-SPEC-007T

M6-SPEC-007T removed immutable provenance fields from model-authored Scientist and Measurement Planner schemas.

The model no longer authored:

- EvidenceSnapshot hash;
- Metric Registry hash/revision;
- human-gate flag.

The trusted host attached those values after structured model output and before the unchanged mechanical verifier.

### Result

The host provenance envelope worked.

The Hypothesis Scientist produced `insufficient_evidence` grounded in the actively inspected evidence. The host attached the exact 64-hex EvidenceSnapshot identity and human gate. Mechanical verification passed, eliminating the hash-transcription failure seen in 007R.

The Measurement Planner then exposed the next transcription boundary.

It proposed a new metric definition for the already registered:

`context_bytes_non_success_mean`

but re-authored the observation as:

`context_bytes_non_success_mean = 6270.666667`

The value 6,270.666667 belongs to `context_bytes_success_mean`, not the non-success mean.

The deterministic Planner verifier rejected the request because the re-authored observation was not one of the actively inspected evidence bindings.

No registry assessment, semantic review, or receipt followed.

### Architectural implication

Once a causal/epistemic observation has been mechanically verified at one stage, a downstream model should not be asked to transcribe it again.

The next Planner contract therefore carries forward through the host envelope:

- verified observation;
- preservation invariants;
- snapshot identity;
- registry identity;
- human gate.

The Measurement Planner should author only what is new at its boundary:

- the registered metric it wants to inspect, or
- the complete definition of a genuinely new measurable axis.

This continues the M6 design trend toward **models authoring semantic choices while the host authors identity, provenance, and already-verified state**.

Evidence artifact SHA-256:

`fa2b2329473e38bccc5d8b74ac44cd985857bc699367a34efbdfbeb348602ef6`


## 33. From Proof-Carrying Structure to Challengeable Semantic Derivations

The derivation-graph design introduces a necessary distinction between structural proof and semantic judgment.

A valid graph root proves only properties that RESIDUAL has formalized and checked. It does not transform natural-language reasoning into scientific truth.

The architecture therefore adds five explicit boundaries.

### Semantic challengeability

Scientist findings, Planner metric decisions, semantic reviews, questions, and ImprovementSpecs are challengeable node classes by schema.

They bind an active challenge policy and cannot opt out of challengeability.

A later Challenge is append-only and targets the immutable semantic node. Open challenges invalidate dependent admission conclusions through declared dependency edges.

Absence of a challenge means only that the current protocol has no unresolved objection; it is not proof that the semantic claim is true.

### Persistent handle resolution

Model-visible evidence handles are invocation-local capabilities rather than content hashes.

Historical replay does not re-resolve those handles against current Host state. The Host records a separate resolution relation from the model-authored citation to the immutable EvidenceFact used during the original invocation.

This preserves deterministic replay without exposing the underlying attestation identity to the model.

### Metric-selection justification

Metric selection is itself a semantic claim.

An ImprovementSpec admission subgraph therefore requires a MetricDecision with a substantive selection rationale, deterministic Host resolution, and independent semantic review.

A mechanically valid metric ID is insufficient.

This directly addresses selection failures that survive transcription hardening.

### Replay boundary

RESIDUAL distinguishes deterministic replay from authorship replay.

Graph validation, Host resolution, formal invariant checks, environment comparison, challenge propagation, and admission recomputation may be replayed without a new model call.

Replacing a challenged Scientist finding, Planner decision, Reviewer verdict, or Human decision requires new authorship and therefore a new graph node.

"Replayable re-derivation" refers only to recomputing deterministic consequences from retained authored nodes.

### Semantic root and execution root

The canonical semantic DAG has an insertion-order-independent graph root.

An executed experiment additionally has an environment-bound execution root committing to the semantic graph root, Environment Contract, observed environment, and input artifacts.

This separates two claims:

- the semantic derivation is the same;
- the experiment executed under the same qualified environment.

Queue latency is retained as an observational environment field unless preregistered otherwise. Required environment drift can block execution admission without changing the semantic graph root.

### Human authorization and execution accountability

Human COSIGN is not merely a terminal admission artifact.

The exact HumanDecision also becomes an authorization root for subsequent ExecutionAction nodes. Execution actions record which admitted ImprovementSpec they implement.

A challenge/revocation of the authorization can therefore invalidate the dependent execution branch without deleting the historical record of what occurred.

### Claim language

The paper should describe the resulting object as a:

> proof-carrying, challengeable derivation graph

where "proof-carrying" is scoped to formalized predicates and attestation integrity.

It should not claim a proof of scientific truth.

The current M6-008 boundary is consequently:

> No candidate has yet produced a complete, unchallenged, environmentally qualified, independently reviewed, exactly human-co-signed ImprovementSpec derivation subgraph satisfying all formal admission predicates.
