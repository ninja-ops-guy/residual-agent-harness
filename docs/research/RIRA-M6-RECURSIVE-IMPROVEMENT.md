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
