# Backward evidence-chain audit

Audit status: **incomplete proof, with explicit missing edges**. No final retained
experiment receipt was supplied to this lane. This document reviews the
implementation and schema at pinned commits; it does not authenticate a real
run. A signature verifies only against an independently trusted Station key.
Self-supplied keys and hashes alone cannot establish authenticity.

| Edge, starting at final IntegrationReceipt | Base `dec5719` | PR81 `30d1d0` | What a reproducer must retain/check |
|---|---|---|---|
| Receipt → Station identity | Ed25519 signature over canonical payload hash, key fingerprint included | Same mechanism | Trusted public-key checkpoint and key lifecycle; rehash payload before verifying signature |
| Receipt → M4 verification policy/revision | No policy/revision hash in v1 | v2 adds signed `verification_policy_hash`, `evidence_level`; payload covers boundary, secops flag, command name/category/argv/time/output limit | Retain exact policy preimage. This does **not** hash external executable bytes, Python packages, OS tools, or container image; those revisions still need explicit hash-bound provenance |
| Receipt → verification outputs | Signed result rows contain stdout/stderr SHA-256, return code and status | Also termination reason and execution boundary | Raw bounded output bytes must be retained under the exact recorded digest. Runners hash streams but these paths do not persist full output blobs. A digest without bytes is not a replayable output |
| Receipt → candidate/accepted tree | Signed `output_commit` resolves to a Git tree, but v1 builds the tree after running commands against a mutable worktree | Signed commit refers to the tree constructed **before** verification from root + signed artifacts, and verification snapshots check mutation | Resolve exact commit and its tree with replacement objects disabled; retain Git objects. A separate `verified_tree` field is not required for indirect Git binding. Source inspection is not independent proof of every filesystem invariant |
| Receipt → IntegrationPlan | Signed `integration_plan_hash` | Same | Retain canonical `EvidenceIntegrationPlan.to_dict()` and recompute `plan_hash` |
| IntegrationPlan/Receipt → worker receipts | Input receipt hashes and order are signed; consumer verifies M3 signatures/bytes and topological dependencies | Same | All worker receipt preimages, trusted key, parent DAG, explicit stale approvals and artifact blobs |
| WorkerReceipt → candidate artifacts and worker verifier revision | Signed artifact path/size/hash/deletion plus `input_commit`, `output_commit`, verifier identity/revision | No new intrinsic verifier implementation registry supplied by the M4 change | Recompute blob hashes and commit trees. A declared 64-character verifier revision is bound, but must resolve to retained implementation/config/policy artifacts before it proves which verifier ran |
| WorkerReceipt → WorkerContract | Signed `contract_hash`; issuer checks RuntimeResult/contract/attempt correspondence | Same | Retain full contract canonical preimage; resolve its exact hash. A hash does not guarantee the preimage was retained |
| WorkerContract → ExecutionPlan | Contract hashes plan identity; `assert_matches_plan` recomputes canonical plan digest and checks task bindings | Same | Retain canonical plan and approval. Freeze/approval metadata is trusted host input, not an independent approval signature |
| ExecutionPlan → frozen workload cell | No workload/cell hash field in canonical plan schema | No closure supplied by #81 | A retained, hash-bound mapping must join protocol hash, workload manifest/task hash, arm, replicate, seed, plan hash and run identity. Similar task names or directory placement do not prove this edge |

The useful distinction is between a field being hash-bound and the complete
preimage graph being available. Worker receipts contain the right contract and
plan references, but a consumer cannot reconstruct missing contracts from their
hashes. Conversely, PR81 fixes material parts of candidate binding and policy
binding; those repairs must not be reported as missing merely because the base
v1 schema lacks them.

Pinned source anchors:

- [Base IntegrationReceipt signature and result schema](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/factory/m4_integrator.py#L108-L176); [base verification then tree creation](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/factory/m4_integrator.py#L499-L557).
- [PR81 v2 receipt and policy field](https://github.com/ninja-ops-guy/residual-agent-harness/blob/30d1d020469d958d90969bc02946145c248e0adb/residual/factory/m4_integrator.py#L126-L197); [snapshot checks and frozen-tree creation](https://github.com/ninja-ops-guy/residual-agent-harness/blob/30d1d020469d958d90969bc02946145c248e0adb/residual/factory/m4_integrator.py#L413-L466); [frozen tree, commit and policy hash](https://github.com/ninja-ops-guy/residual-agent-harness/blob/30d1d020469d958d90969bc02946145c248e0adb/residual/factory/m4_integrator.py#L579-L650).
- [PR81 bounded output hashing](https://github.com/ninja-ops-guy/residual-agent-harness/blob/30d1d020469d958d90969bc02946145c248e0adb/residual/factory/m4_sandbox.py#L127-L284); [fixture output hashing](https://github.com/ninja-ops-guy/residual-agent-harness/blob/30d1d020469d958d90969bc02946145c248e0adb/residual/factory/m4_safety.py#L181-L259).
- [Worker receipt canonical payload/signature](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/factory/evidence_receipts.py#L105-L201); [issuer correspondence checks](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/factory/station_issuer.py#L50-L96); [consumable receipt/byte validation](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/factory/evidence_bus.py#L198-L235).
- [Contract → plan checks](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/factory/worker_contract.py#L163-L197); [plan canonical schema](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/factory/models.py#L65-L149).

Acceptance criteria for a future independent auditor: ingest one signed final
receipt plus an immutable artifact manifest and trusted key; resolve every hash
without a model or network request; verify each preimage and identity mapping;
rebuild the exact tree and all metric inputs; reject missing, conflicting,
duplicate or stale edges. Missing implementation revisions and missing output
bytes must produce `INCOMPLETE`, not a qualified proof. Separate evidence
integrity from correctness of the verifier and truth of the original workload.
