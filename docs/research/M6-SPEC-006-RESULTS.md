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

## Lessons supported by the experiment

### 1. Repair should be corrective, not regenerative
Supplying the previous candidate alongside exact failure findings allowed the model to preserve working portions and repair successively narrower defects.

### 2. Clean worktrees and repair context are compatible
The next attempt still began from a clean baseline. Prior failed source was context, not trusted mutable state.

### 3. Mechanical checks should precede semantic review
The reviewer was not invoked until deterministic checks passed. Failed candidates therefore consumed no reviewer authority.

### 4. Bounded extra attempts can materially improve completion
Earlier M6 experiments were artificially capped at three by Mission Control despite Store permitting five. A shared ceiling removes that inconsistency while retaining a hard bound. M6-006 succeeded on attempt three, so it did not require attempts four or five, but the deterministic regression suite separately proves fourth-attempt success remains possible without weakening checks.

### 5. Transport/source clarity matters
After the runner contract explicitly separated the outer JSON envelope from literal source contents, the small-model data-object failure seen in M6-SPEC-003 disappeared.

### 6. Runtime provenance is part of experiment validity
A dedicated Ollama endpoint eliminated the ambiguous port-ownership condition observed in earlier trials.

### 7. More output capacity is not automatically better
M6-SPEC-005 raised the 7B output ceiling to 4096 and timed out before producing a candidate. Restoring the empirically adequate 1600-token ceiling produced a complete three-attempt repair sequence.

## What this demonstrates

M6-SPEC-006 demonstrates that, for this bounded task and configuration, RESIDUAL can use a real local coding model to generate a component intended for its own architecture, reject two incorrect candidates, feed verified failure evidence into subsequent bounded repair attempts, obtain a candidate satisfying unchanged deterministic tests, submit only that candidate for review, integrate the exact reviewed revision, issue a verification receipt, and export the resulting source.

## What this does not demonstrate

This is one successful task and must not be generalized to arbitrary autonomous self-improvement. It does not establish:
- general coding reliability;
- autonomous discovery of the improvement objective;
- superiority of the generated successor to the running harness;
- permission for a candidate to modify its evaluator;
- permission for RESIDUAL to self-promote or deploy a successor.

Those remain later M6 research stages.

## Integration decision

The repair-loop lessons are suitable for production integration because they improve corrective context and bounded execution without weakening any acceptance, review, receipt, M4, quarantine, integration, or promotion authority boundary.
