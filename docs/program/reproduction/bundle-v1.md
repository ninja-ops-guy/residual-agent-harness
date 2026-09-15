# Experiment bundle v1

Status: versioned preparation contract, not an independently preregistered study.
Schema ID: `residual.experiment-bundle.v1`. Reproduction report ID:
`residual.reproduction.v1`. Reports include descriptive three-objective Pareto
dominance with explicit incomplete-point handling; no inference is performed. Changes to fields or meanings require a new schema.
No receipt schema, M4 implementation, or existing live evaluation lock is changed.

Each run occupies `<runs-dir>/<run-id>/`. `run-id` and pairing identifiers use
`[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`. All indexed paths are relative POSIX paths.
A raw artifact SHA-256 is distinct from a native receipt hash, Git object ID,
workload's internal digest, or a canonical-JSON hash.

| Path | Required content and purpose |
| --- | --- |
| `manifest.json` | Schema, run ID, evidence mode, full expected schedule, artifact hashes/byte lengths, declared source coverage. This file does not hash itself. |
| `metadata/environment.json` | OS, Python version, dependency inventory, extension details such as CPU, kernel, container digest and namespace configuration. |
| `metadata/git.json` | Exact commit/tree IDs, dirty flag, extension details. For dirty runs retain patch bytes as an attachment and reference their hash in details. |
| `metadata/workload.json` | Workload ID and full expected schedule, exactly equal to manifest schedule. The file itself supplies a workload artifact SHA-256. Retain native workload definitions and graders as attachments. |
| `metadata/models.json` | Requested/observed model identities, provider, generation parameters; unresolved observed revision remains null. |
| `metadata/prompts.json` | Prompt IDs and retained content path/hash. Prompt bytes belong in `attachments/`. |
| `metadata/protocol.json` | Protocol ID, preparation/frozen status, retained document path and raw SHA-256. The document belongs in `attachments/`. |
| `records/cells.jsonl` | Raw terminal execution, reported acceptance, independent grading and test counters, one row per recorded scheduled cell. |
| `records/usage.jsonl` | One normalized reservation/completion row per provider attempt, including failed/retried calls. An incomplete reservation stays RESERVED with unknown fields. |
| `records/timing.jsonl` | One cell timing/local cost record with explicit usage coverage. |
| `records/failures.jsonl` | Failure identities, stage, kind, detail and retained source references. |
| `evidence/receipts.jsonl` | Existing native receipt envelopes, including integration/worker/contract/plan references where available. Retained opaque; signature/chain interpretation is deferred. |
| `evidence/scheduler.jsonl` | Native scheduler trace envelopes. Retained opaque; cannot become authoritative acceptance. |
| `evidence/verifier.jsonl` | Native verifier revision, outputs and evidence envelopes. Retained opaque; cannot become independent ground truth. |
| `streams/stdout.bin`, `streams/stderr.bin` | Retained process output bytes. Per-process streams may also be indexed under attachments. Never executed or interpreted as instructions. |
| `reproduce.txt` | Exact human-readable offline reproduction command. Retained as bytes and never executed by the replay tool. |
| `attachments/**` | Optional additional retained files: native workload, prompt, grader, source, patch, logs, pricing, environment, proof and detached trust artifacts. Every consumed/reference target must be indexed. |

Every core file above exists, even when empty. Evidence JSONL and stdout/stderr may
be empty with `source_coverage` explaining `not_applicable` or `unavailable`.
Missing a core file is an integrity error, not an empty log. A missing terminal
cell row is an analytical MISSING outcome. This distinction preserves failures
without pretending missing artifact bytes were retained.

Maximums: 4,096 indexed artifacts; 32 MiB per file (including manifest); 128 MiB
indexed bytes in a bundle; 100,000 scheduled cells; 256 comparison configurations
for bounded pairwise Pareto analysis. This bounded format is not a
100,000-worker scalability claim. Large soak logs need a subsequent streaming
schema. Single-link regular files only; no hardlinks, symlinks, devices, sockets,
FIFOs, archive extraction or executable hooks. Unknown extra files are not input;
only indexed bytes participate in the report. Do not place secrets in either.

## Exact manifest fields

```json
{
  "schema_version": "residual.experiment-bundle.v1",
  "run_id": "run-001",
  "evidence_mode": "synthetic",
  "expected_cells": [
    {"cell_id":"R0-task1","family_id":"family1","task_id":"task1",
     "repeat_index":0,"configuration":"R0","model_class":"strong",
     "topology":"strong-only"}
  ],
  "artifacts": [
    {"path":"records/cells.jsonl","sha256":"<64 lowercase hex>","bytes":123}
  ],
  "source_coverage": {
    "receipts":{"status":"unavailable","reason":"Collector not connected."},
    "scheduler":{"status":"unavailable","reason":"Collector not connected."},
    "verifier":{"status":"unavailable","reason":"Collector not connected."},
    "stdout":{"status":"not_applicable","reason":"No process ran."},
    "stderr":{"status":"not_applicable","reason":"No process ran."}
  }
}
```

This is an abbreviated field illustration; a valid bundle indexes **all** core
files plus its attachments. The executable complete fixture is under
`examples/reproduction/synthetic-demo/`. Only `synthetic` and `measured` are allowed
modes; neither is independently authenticated. Pair tuples are unique as well as
cell IDs. `repeat_index` is a nonnegative integer, never a boolean. Exact expected
rows are frozen before execution; merely counting the number of result rows is
insufficient.

## Metadata schemas

Only the listed fields are allowed; `details` and `parameters` are explicit JSON
object extension points. JSON is UTF-8, duplicate keys and nonfinite numbers are
rejected, and strings/identifiers must be nonempty where specified.

| File | Exact fields |
| --- | --- |
| environment | `os: string`, `python: string`, `dependencies: string[]`, `details: object` |
| git | `commit: 40-or-64 lowercase hex`, `tree: 40-or-64 lowercase hex`, `dirty: bool`, `details: object` |
| workload | `workload_id: identifier`, `expected_cells: full manifest schedule` |
| models | `models: [{model_id: identifier, provider: string, requested_revision: string, observed_revision: string-or-null, parameters: object}]` |
| prompts | `prompts: [{prompt_id: identifier, path: indexed-relative-path, sha256: raw-file-digest}]` |
| protocol | `protocol_id: identifier`, `status: preparation-or-frozen`, `document_path: indexed-relative-path`, `document_sha256: raw-file-digest` |

Prompt/model IDs are unique. Prompt/protocol references must match the indexed
retained bytes. Git IDs and metadata are assertions whose syntax is checked; this
command does not call Git or prove the commit/tree exists. Future paper admission
must check its externally qualified Git identity and verifier boundary evidence.

## Raw JSONL schemas

Each file contains zero or more JSON object records, each ending with a newline.
No blank lines, comments, torn terminal records, unknown fields, NaN or Infinity.
Nullable numeric values mean unknown; nonnull numbers are finite/nonnegative.
Token/test/conflict counts and attempt/repeat indices are integers, not booleans.
Every `cell_id` names a scheduled cell. Every `source_refs` value is a unique array
of indexed relative paths. The content of a reference is not automatically proof.

| File | Exact fields |
| --- | --- |
| cells | `cell_id`, `execution_status`, `verifier_status`, `correctness_status`, `accepted: bool-or-null`, `reworked: bool-or-null`, `merge_conflicts: int-or-null`, `tests_passed: int-or-null`, `tests_total: int-or-null`, `source_refs` |
| usage | `call_id`, `cell_id`, `attempt: int`, `provider`, `model_id`, `role`, `status`, `input_tokens: int-or-null`, `output_tokens: int-or-null`, `cost_usd: number-or-null`, `elapsed_seconds: number-or-null`, `source_refs` |
| timing | `cell_id`, `elapsed_seconds: number-or-null`, `gpu_seconds: number-or-null`, `coordination_seconds: number-or-null`, `local_cost_usd: number-or-null`, `usage_complete: bool`, `source_refs` |
| failures | `failure_id`, `cell_id`, `stage: string`, `kind: string`, `detail: string`, `source_refs` |

Allowed cell execution values: `COMPLETED`, `TIMEOUT`, `CRASH`, `ERROR`, `UNKNOWN`,
`NOT_RUN`. `MISSING` is generated only by replay for absent expected rows. Allowed
verifier values: `PASS`, `FAIL`, `UNKNOWN`, `ERROR`, `SKIPPED`. Allowed independent
ground-truth values: `CORRECT`, `INCORRECT`, `UNKNOWN`, `NOT_GRADED`. Correctness on a
rejected candidate may be retained; it is not counted as an accepted success.

Usage roles: `worker`, `coordinator`, `verifier`, `grader`. Usage states:
`COMPLETED`, `TIMEOUT`, `ERROR`, `UNKNOWN`, `RESERVED`. Every `model_id` resolves in
model metadata. Each retry has a distinct `call_id`; `attempt` retains its ordinal.
A normalized reservation/completion row is assembled by a future trusted collector;
v1 does not prove all transport calls were captured. `usage_complete` must remain
false when reconciliation is unavailable. Preserve raw ledger events as attachments.

One terminal row per cell and one timing row per cell; duplicate IDs are errors.
`call_id` and `failure_id` are independently unique. Test totals and passed counts
are both null or both integers with passed <= total. Cell coordination seconds do
not exceed cell elapsed seconds. Cells with accepted=true and an invalid execution
or verifier status are retained as observable invariant violations, not rejected
before analysis. No primary-study exclusions are inferred from these records.

## Build and retain procedure

1. Prepare the protocol, expected schedule, identities, prompt/workload contents,
   and declared source/usage coverage. Keep an external pre-execution commitment to
   the protocol/schedule. This repo does not supply that independent registry.
2. Record raw outcomes and accounting through the execution collector. Never put
   cached aggregates in place of cell records. Preserve failures and incomplete
   reservation rows. Redact secrets at collection time and document redactions.
3. Materialize the exact core files and optional attachments, calculate each raw
   file hash and byte length, then write the immutable manifest. A native exporter
   is not included in this increment.
4. Retain the manifest SHA-256 through an independently trusted channel, together
   with the qualified source revision and analysis implementation revision.
5. Reconstruct with `residual reproduce <run-id> --runs-dir <dir>
   --manifest-sha256 <external-digest> --output <new-report-path>`.
6. Retain the report and command independently. Validate the native chain and
   frozen analysis gates before admitting any report to the paper.
