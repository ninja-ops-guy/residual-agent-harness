# SPEC-BEND-INTEGRATION-001 — Optional Bend 2 Proof and Compute Adapter

**Status:** Proposed / experimental
**Target:** research adapter only
**Upstream:** bendlang/bend, Bend 2

## 1. Scope

RESIDUAL MAY integrate Bend 2 as:
1. a proof-checking verifier backend; and
2. later, an optional pure-compute execution backend.

Bend MUST NOT become a trusted authority root or mandatory runtime dependency in this phase.

## 2. Version pinning

Every Bend execution MUST bind:
- Bend version/commit identity;
- runtime/compiler target;
- host platform;
- toolchain dependencies;
- source hashes;
- law/proof hashes.

Unpinned toolchain execution MUST be UNKNOWN or rejected for authoritative evidence.

## 3. Proof verifier

A `BendProofVerifier` MUST run out of process.

It MUST consume:
- protected `LAWS.bend`;
- candidate implementation/proof files;
- execution limits;
- pinned toolchain identity.

It MUST emit a normalized verification result with:
- PASS / FAIL / UNKNOWN;
- exit code;
- bounded stdout/stderr;
- law hash;
- proof hash;
- candidate tree hash;
- toolchain hash/identity;
- elapsed time;
- termination reason.

A Bend PASS MUST NOT itself issue a receipt, integrate code, promote a candidate, or merge a branch.

## 4. Protected law ownership

The worker being evaluated MUST NOT be able to modify the protected law set used to evaluate that candidate.

Changing law content creates a new verifier contract/revision.

A candidate MUST NOT receive credit from a proof checked against a law set different from the hash bound in the ImprovementTask/WorkerContract.

## 5. Unsafe and foreign boundary

The initial trusted verifier profile MUST reject:
- `@unsafe`;
- foreign C imports;
- foreign JS imports;
- unapproved external packages;
- dynamic toolchain fetches during verification.

A future profile MAY permit some of these only under a separate explicit policy and sandbox qualification.

## 6. Sandbox

Bend compiler/checker/runtime execution MUST use the ordinary RESIDUAL sandbox/resource-control path.

At minimum enforce:
- wall-clock deadline;
- CPU limit;
- memory limit;
- PID/process limit;
- filesystem scope;
- network policy;
- process-tree termination.

Toolchain crashes or ambiguous termination MUST be UNKNOWN/FAIL according to frozen policy, never PASS.

## 7. Proof plus behavioral verification

For security- or authority-relevant code, Bend proof verification SHOULD be additive to existing behavioral verification.

A proof result MUST NOT silently replace:
- integration tests;
- M4 checks;
- sandbox qualification;
- independent behavioral tests;
- receipt binding.

## 8. Evidence model

Bend evidence MUST be append-only and include:
- law source hash;
- candidate source hash;
- proof source hash;
- Bend binary/version;
- compile/check command identity;
- normalized result;
- diagnostics hash;
- optional produced binary hash.

Evidence MUST distinguish source-level proof checking from runtime execution.

## 9. Optional compute backend

A future `BendComputeBackend` MAY execute approved Bend programs for pure compute tasks.

It MUST require:
- explicit task opt-in;
- runtime target selection;
- sandbox limits;
- no authority expansion;
- deterministic input snapshot;
- output verification.

GPU execution MUST NOT be assumed beneficial. Qualification SHOULD compare CPU/GPU/native baselines for the specific workload.

## 10. Routing

The CapabilityRouter MAY advertise Bend capabilities such as:
- bend.proof_check;
- bend.cpu_parallel;
- bend.gpu_parallel.

Capability advertisement MUST NOT automatically route production work to Bend.

Selection MUST remain deterministic and policy-bound.

## 11. Failure semantics

The adapter MUST distinguish:
- proof_false;
- proof_open;
- syntax/type_error;
- unsupported_unsafe;
- unsupported_foreign;
- toolchain_missing;
- toolchain_crash;
- timeout;
- resource_limit;
- sandbox_failure;
- runtime_failure;
- unknown.

No error category may be normalized to PASS.

## 12. Minimum acceptance tests

### BEND-R1 — Law immutability
Worker modification of protected laws is rejected.

### BEND-R2 — Version binding
Changing Bend version/toolchain changes evidence identity.

### BEND-R3 — Unsafe rejection
Any `@unsafe` candidate is rejected in the initial profile.

### BEND-R4 — Foreign import rejection
Foreign C/JS imports fail the initial profile.

### BEND-R5 — Proof failure
An invalid or open law produces non-PASS.

### BEND-R6 — Proof success
A valid proof produces PASS only for the Bend verifier, not automatic integration.

### BEND-R7 — Sandbox timeout
A hung checker/runtime is terminated and cannot yield PASS.

### BEND-R8 — Evidence binding
Law/proof/candidate hashes in the result match exact checked bytes.

### BEND-R9 — Behavioral independence
A Bend PASS does not bypass another configured mandatory verifier.

### BEND-R10 — No authority expansion
Enabling Bend capabilities does not enlarge WorkerContract authority.

### BEND-R11 — Toolchain unavailable
Missing Bend/compiler dependencies produce explicit UNKNOWN/BLOCKED according to policy.

### BEND-R12 — Compute opt-in
GPU/parallel execution is never selected unless task/profile explicitly allows it.

## 13. Qualification experiment

The first experiment SHOULD select 3–5 small pure invariants already represented by deterministic Python tests.

For each invariant:
1. encode a host-owned Bend law;
2. generate/author candidate implementation + proof;
3. run Bend proof check;
4. run existing behavioral check;
5. compare repair iterations, latency, and diagnostic usefulness;
6. retain disagreements.

The experiment MUST report underspecified-law failures separately from compiler/proof failures.

## 14. Exit criteria

Promote beyond research only if:
- exact-version checker operation is stable;
- proof generation/repair is bounded and reproducible enough to be useful;
- proof evidence adds information beyond existing tests;
- sandbox/resource behavior is qualified;
- maintenance/toolchain burden is acceptable;
- no authority shortcut appears.

## 15. Non-goals

This spec does not:
- rewrite RESIDUAL in Bend;
- replace Factory scheduling with Bend;
- treat GPU execution as universally faster;
- treat Bend proof success as proof of compiler correctness;
- allow Bend to authorize merge/promotion;
- claim foreign/unsafe code is covered by the initial proof boundary.
