# Verifier corpus, outcome accounting, and M4 compatibility

This lane delivers a frozen engineering corpus, an offline outcome scorer,
15 fault-injection designs, and a read-only Swarm B review. It changes no runtime
API, existing PR branch, acceptance authority, or confirmatory experiment result.

## Exact-head review

| Source | Reviewed commit | Scope |
| --- | --- | --- |
| Base main | `dec571992a97b4ae80f0310aa32ffd8f542aef8c` | Corpus lane starting point |
| [Swarm B PR #41](https://github.com/ninja-ops-guy/residual-agent-harness/pull/41) | `9dd0955afaf146719bcf9c8ff27d9dd14021fc4a` | VQ benchmark, outcomes, profile, replay, gate |
| [M4 PR #81](https://github.com/ninja-ops-guy/residual-agent-harness/pull/81) | `30d1d020469d958d90969bc02946145c248e0adb` | Runner status/termination reasons and failure attribution |

These are immutable source observations, not a statement about a later PR head
or the eventual merge. Source blob IDs and SHA-256 values plus synthetic API
probe outputs are retained in [`vq-head-audit.json`](vq-head-audit.json).
Reproduce them without fetching or modifying a branch when these Git objects are
present locally:

```sh
python docs/program/verifier/probe_vq_exact_head.py > /tmp/vq-head-audit.json
```

The probe imports exact VQ/core sources in a temporary namespace package, omits
the unrelated top-level package initializer, and performs no model or candidate
execution. M4 was source-reviewed, not live-executed by this probe.

| Finding | Evidence | Required integration decision |
| --- | --- | --- |
| **Execution UNKNOWN/ERROR have no VQ outcome representation.** | `vq/outcomes.py:LabeledOutcome.verdict` is boolean. `vq/benchmark.py:VerifierBenchmark.run` applies `bool(verifier_fn(...))`. Synthetic returns `"unknown"`, `"error"`, or `"fail"` are all retained as acceptance; an exception aborts the benchmark without a returned report. | Do not directly pass a typed M4 result/string/object to this boolean callback. Add a typed adapter and retain every attempted case, including errors and abstentions, before integrating these APIs. This demonstrates an API integration hazard, not an existing M4 exploit or proof of current wiring. |
| **Coverage can hide missing execution.** | `vq/profile.py:from_outcomes` computes coverage as `n/n` on the already-retained boolean outcomes. `MetricEstimate.status=UNKNOWN` means too few samples, not a verifier abstention. | Coverage denominator must be the complete frozen attempted/scheduled set according to the analysis plan. Preserve missing, skipped, UNKNOWN, infrastructure error, timeout, output-limit and signal categories separately. |
| **M4 provides distinctions the VQ adapter must preserve.** | `m4_sandbox.py:run_isolated` distinguishes setup ERROR, unavailable/launch UNKNOWN, and candidate normal-exit FAIL. `m4_integrator.py:_verification_available` accepts attribution only for nonnegative normal exits and PASS/FAIL; resource terminations and UNKNOWN/ERROR are excluded. | A blocked launch or unavailable sandbox is not a verifier false reject. A timeout is not automatically a semantic mistake. No quality update without an independently labeled artifact and an attributable verifier decision. |
| **Class orientation differs across current modules.** | PR41's recall is `TA/(TA+FR)`: recall of acceptable artifacts. The baseline `assurance/quality.py` exposes defect recall as `TR/(TR+FA)`. The retained probe has TA=2, FA=1, TR=3, FR=1 and reports recall=0.666667 while defect recall is 0.75. | Name both measures explicitly. Do not present acceptance recall as defect detection recall. Keep the label orientation and denominators in every table. |
| **Replay admits malformed boolean representations.** | `VerifierBenchmark.recompute_from_outcomes` uses `bool(d["verdict"])` and `bool(d["ground_truth"])`. The string `"false"` becomes true; `LabeledOutcome` does not enforce exact boolean types. | Strict JSON schema/type admission is needed before trusted replay. Reject ambiguous strings, integers, non-finite values, duplicate IDs and unknown fields. Hash-valid malformed data remains malformed. |
| **Calibration intervals need a different statistical model.** | `vq/profile.py` computes one minus mean absolute confidence error for decision correctness, rounds its sum to an integer, then applies a Wilson binomial interval. | Name the confidence target and scoring rule explicitly. Do not describe a Wilson interval over rounded continuous scores as justified binomial uncertainty. Use the frozen analysis plan for calibration estimation/uncertainty. |

What is already useful in PR41: it rejects worker-self-reported label sources,
keeps artifact-only inputs separate from fixture labels during `run`, hashes
verifier implementation/configuration/policy identity, stores raw labeled
outcomes, and uses a lower precision bound for safety-critical gating. These
mechanisms do not resolve the missing typed execution adapter by themselves.

The audit does not establish a calibrated verifier, a sandbox vulnerability,
cryptographic authenticity of labels, or a production acceptance rate. The small
synthetic probes intentionally exercise API edge cases, not representative tasks.

## Outcome contract

The preflight scorer is independent of PR41 and imports no Residual runtime.
It validates locked corpus hashes and scores supplied retained decisions; it
cannot accept a tree, issue a receipt, authorize a capability, or call a model.

Input JSON has exactly these fields:

| Field | Required value |
| --- | --- |
| `schema` | `residual.preflight.verifier-observations.v1` |
| `corpus_manifest_sha256` | Frozen corpus manifest SHA-256 |
| `verifier_revision_sha256` | 64 lowercase hexadecimal characters; one exact revision per report |
| `observations` | List of `{case_id, evidence_sha256}`; at most one attempt per case |
| `evidence` | Map of digest to the complete evidence blob, with no unreferenced blobs |

Each evidence blob has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `residual.preflight.verifier-evidence.v1` |
| `case_id` | Neutral frozen candidate ID |
| `candidate_sha256` | Exact candidate-file SHA-256 from the locked manifest |
| `verifier_revision_sha256` | Must match the report revision |
| `status` | `pass`, `fail`, `unknown`, `error`, or `skipped` |
| `termination_reason` | `exit`, `timeout`, `output_limit`, `sandbox_error`, `launch_failed`, `isolation_unavailable`, `signal`, `not_run`, or `verifier_error` |
| `returncode` | Strict integer or JSON null; never a boolean |
| `source` | `synthetic-accounting-test` or `retained-run` |

Evidence digests use SHA-256 of ASCII JSON with sorted keys, compact comma/colon
separators, and no non-finite numbers. There is no newline in the hashed form.
Do not cast statuses to booleans. The scorer verifies consistent case/candidate/
revision bindings and digest references; **it does not authenticate the reporting
party, verify Station signatures, or prove that the reported execution occurred**.
A retained experiment must also retain and authenticate the underlying M4 artifacts
through the experiment bundle/evidence auditor. `source` is a declared provenance
label, not a trust upgrade.

Missing cases remain in the frozen denominator. Retry observations require a
separate preregistered attempt table/report and selection policy; duplicate case
IDs are rejected so a later successful attempt cannot silently replace a failure.
The current utility scores a single attempt per case and does not aggregate
retries, confidence values, bootstrap intervals or calibration curves.

| Input outcome | Scoring treatment |
| --- | --- |
| PASS, ordinary zero exit | True or false acceptance according to evaluator gold |
| FAIL, ordinary positive exit | True or false rejection according to evaluator gold |
| UNKNOWN | Separate abstention/unavailable count; never PASS or FAIL |
| ERROR | Separate execution/infrastructure count |
| Timeout or output limit | Separate resource-limited count, including when the runner says FAIL |
| Signal or negative return code | Separate signal count |
| SKIPPED | Separate count; must have reason `not_run` and null return code |
| No retained observation | Separate missing count |

The adapter is responsible for distinguishing an ordinary verifier rejection
from a test-framework/configuration exception. Exit code 1 alone cannot establish
semantic attribution. Store classifier evidence in the underlying experiment
bundle and emit an error outcome when the verdict itself was unavailable.

Counts reconcile to every frozen case, both overall and by category/gold class.
Unavailable and missing cases are excluded from conditional confusion metrics
but remain in `decision_coverage`. Zero-denominator metrics are null, never 0 or 1.

| Metric | Definition |
| --- | --- |
| Acceptance precision | `TA / (TA + FA)` |
| Acceptance recall | `TA / (TA + FR)` |
| Defect precision | `TR / (TR + FR)` |
| Defect recall | `TR / (TR + FA)` |
| False-accept rate on decided defects | `FA / (FA + TR)` |
| False-reject rate on decided controls | `FR / (FR + TA)` |
| Decision coverage | `(TA + FA + TR + FR) / all frozen cases` |
| Unsafe accepts per frozen defect | `FA / all frozen defects`; report alongside coverage |

Always report raw denominators, missingness and class balance. Eight designed
defects do not estimate real-world prevalence, and repeated runs on the same
case are not independent new challenge samples. No confidence, calibration,
production safety, or economic claim is authorized by this toy score.

## Fault-injection execution gate

The complete matrix is
[`experiments/preflight/adversarial/fault-matrix.json`](../../../experiments/preflight/adversarial/fault-matrix.json).
It includes worker timeout/crash, malformed response, duplicate/stale receipt,
network loss, provider 429/500, corrupted Git object, verifier timeout,
scheduler/Station restart, evidence-sink interruption, disk full and partial write.

Every trial needs an observed injection event at the intended boundary, retained
pre/post authority state, terminal/recovery evidence, and a fixed external deadline.
An absent fault event is INVALID; a missing prerequisite is BLOCKED; an assertion
or mock alone is not evidence of a production recovery. An unexpected acceptance
is a safety failure even if the framework labels the run inconclusive. Fault
containment statistics are separate from verifier semantic precision/recall.

Scheduler/Station crash recovery is blocked on stable documented durability and
fencing semantics. Disk-full injection requires a fault adapter or disposable
quota-limited filesystem; it must never fill the host. Git corruption targets
only a disposable copy. All matrix entries remain unexecuted in this change.

## Verification and limitations

`tests/test_adversarial_corpus.py` exercises independent witnesses, strict JSON,
frozen hashes, rewritten-manifest rejection, label-free export, FIFO/symlink
rejection, duplicate attempts, stale/tampered evidence, class orientation,
missingness and UNKNOWN/error/resource accounting. The CLI rejects malformed
input with a controlled nonzero result and never emits candidate control bytes
as raw terminal escapes.

The local loader rejects symlinks, hardlinked files and nonregular files and
bounds individual input sizes. It is not a replacement for descriptor-relative
M4 filesystem isolation and does not claim protection from a concurrent
same-UID host attacker modifying its root or executable. Integrity depends on
the reviewed code and pinned content hash being trusted.
