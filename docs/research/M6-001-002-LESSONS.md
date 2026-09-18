# M6 Self-Hosting Lessons Learned — Experiments 001–002

## Executive summary

Two frozen self-hosting trials failed closed:

- **M6-SPEC-001** — Qwen2.5-Coder 1.5B, 3 calls, 5,526 tokens, 125.374 s.
- **M6-SPEC-002** — Qwen2.5-Coder 7B, 3 calls, 5,336 tokens, 432.543 s.

Neither trial integrated a candidate or reached review, receipt issuance, export, or promotion.

The strongest harness-level lesson is that the existing repair path supplies failure findings but not the previous failed candidate's writable file contents. Each repair attempt starts in a clean baseline worktree. This preserves safety, but without prior candidate context it converts corrective repair into partial regeneration.

M6-SPEC-002 is especially diagnostic: the 7B model produced three different, progressively narrower defects across its three attempts:
1. invalid `dataclasses.frozen` import;
2. missing `json` import;
3. missing blank-string validation.

The model was moving toward the contract, but the harness did not explicitly bind the previous candidate into the next repair request.

## Observations

### M6-SPEC-001
- attempt 1: source compiled but did not expose `ImprovementSpec`;
- attempt 2: unclosed parenthesis;
- attempt 3: structured response hit the 1,600-token output ceiling;
- outcome: escalated after 3 passes.

### M6-SPEC-002
- attempt 1: source compiled but imported nonexistent `dataclasses.frozen`;
- attempt 2: source compiled but `canonical_json()` referenced missing `json`;
- attempt 3: source compiled but accepted a whitespace-only `improvement_id`;
- outcome: escalated after 3 passes.

The larger model removed the truncation failure but did not complete within the same bounded attempt envelope.

## Root-cause hierarchy

### L1 — Candidate-quality defects
The models produced objectively invalid or incomplete implementations. Verification correctly rejected them.

### L2 — Repair-semantic weakness
On `repair_required`, RESIDUAL preserved the failure findings but generated a fresh candidate from the project baseline. The packet did not include the previous attempted writable files. A model therefore had to reconstruct the implementation and infer the correction from findings alone.

### L3 — Bounded-attempt interaction
The Mission control plane caps a single-task batch at three passes through:

`max_passes = min(batch_max_passes, len(tasks) * 3)`

and dispatches tasks only while `attempt < 3`.

Thus setting `batch_max_passes=5` did not allow five implementation attempts for this one-task experiment. This behavior is safe and bounded, but experiment configuration must not describe `batch_max_passes` as synonymous with task repair attempts.

### L4 — Evidence-retention gap in the experiment apparatus
RESIDUAL internally retained failed-attempt check/patch artifacts, but the temporary Station used by the experiment was destroyed after the script completed. M6-SPEC-001/002 evidence therefore preserved final state and events but not all prior candidate contents.

### L5 — Provider-process provenance
M6-SPEC-001 observed an already-bound Ollama port. The run still made valid local model calls, but experimental workflows should explicitly own and record the provider process.

## Changes derived from the failures

### Repair context
When a task enters a later attempt:
- retain a **fresh baseline candidate worktree**;
- read only the previous candidate's declared writable files;
- provide those contents under `prior_candidate_files`;
- provide the existing `repair_findings`;
- instruct the model to correct the prior candidate and return full replacement file contents;
- never implicitly carry failed source into the fresh candidate.

This preserves the security benefit of clean worktrees while allowing actual corrective editing.

### Repair-context provenance
Record the hashes of prior candidate files bound into the repair request. This proves that a later attempt had access to a specific prior implementation without placing raw source into ordinary event metadata.

### Research evidence retention
Experiment apparatus should persist:
- per-attempt check receipts;
- candidate patches where produced;
- artifact hashes and sizes;
- generated source hash;
- provider/runtime identity;
- task transitions;
- timing and token usage;
- final brake and outcome.

### Process ownership
Research workflows should terminate stale local model servers, start the intended process explicitly, retain its PID/log, and record the installed model inventory.

## What is not being changed

These lessons do **not** justify weakening:
- acceptance checks;
- reviewer independence;
- verification receipts;
- M4 authority boundaries;
- integration checks;
- evidence integrity;
- human promotion authority.

The correct response to model failure is better corrective context and better evidence, not easier acceptance.

## Follow-up experiment

**M6-SPEC-003** is preregistered against the exact M6-SPEC-001 historical baseline. It keeps the 1.5B model, task specification, behavioral checks, 1,600-token output ceiling, budgets, and authority boundaries fixed.

The intervention is only:
1. previous failed writable files are supplied as bounded repair context;
2. repair-context hashes are recorded;
3. richer failed-attempt evidence is retained.

If M6-SPEC-003 succeeds after a failed first attempt, that supports the repair-context hypothesis. If it succeeds on the first attempt, the intervention was not exercised. If it fails, the retained candidate artifacts should make the next failure analysis substantially more precise.


## M6-SPEC-003 result

The repair-context intervention was exercised on the same 1.5B task and still failed closed.

- 3 calls
- 4,171 reported tokens
- 41.72 s mission wall clock
- final outcome: escalated
- integrated: 0/1

The richer evidence changed the diagnosis materially. Attempt patches showed:

1. attempt 1 wrote only `{` into `spec.py`;
2. attempt 2 wrote a dict/JSON-like data object instead of Python source;
3. attempt 3 repeated the data-object pattern and changed one acceptance value.

Repair-context hashes prove the prior candidate was supplied on attempts 2 and 3, so the remaining failure cannot be explained by missing repair context alone.

### New lesson: transport/source conflation

The runner protocol uses a structured outer JSON envelope:

`{"files":{"path":"complete file content"}}`

For a small model, that envelope can be confused with the required contents of the target file. M6-SPEC-003 shows the model satisfying the transport shape while placing a data object inside the `.py` file rather than implementing the requested class.

The runner contract is therefore being strengthened to state explicitly that:
- the outer JSON is transport only;
- each value is literal file content;
- `.py` values must contain Python source;
- a concrete correctly escaped Python example is provided.

This does not change acceptance, review, receipts, integration, M4, or promotion authority.

## M6-SPEC-004 hypothesis

M6-SPEC-004 should compare directly against M6-SPEC-003 while keeping the same 1.5B model, frozen task/checks, repair-context intervention, token ceiling, and attempt envelope. The only new behavioral intervention is the transport/source disambiguation in the runner system contract.

A successful first attempt would support the transport-clarity hypothesis but would not test repair. A failed first attempt followed by a successful repair would support both transport clarity and repair-context composition.
