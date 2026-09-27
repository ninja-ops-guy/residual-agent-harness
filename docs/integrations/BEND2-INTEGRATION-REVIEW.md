# Bend 2 Integration Review for RESIDUAL

**Project:** Bend 2
**Website:** https://bend-lang.com/
**Repository:** https://github.com/bendlang/bend
**Reviewed:** 2026-09-18

## Verdict

Bend 2 is potentially useful to RESIDUAL, but only as an **optional experimental proof/parallel-compute backend**.

It should not become a core runtime dependency yet.

The strongest integration value is not "rewrite RESIDUAL in Bend." It is:

1. mechanically checked laws/proofs for narrow high-value invariants;
2. a deterministic proof gate that can complement RESIDUAL's verifier/receipt model;
3. optional CPU/GPU acceleration for pure, balanced, compute-heavy kernels;
4. a potentially useful target for AI-generated code that must satisfy explicit laws.

## Why it fits RESIDUAL unusually well

Bend's law/proof model resembles RESIDUAL's core philosophy: workers may propose code, but acceptance should depend on independent machine-checkable conditions.

A Bend project conventionally separates:

- `LAWS.bend` — claims/invariants, ideally human/host-owned;
- `PROOF.bend` — proofs plus implementation, which the AI may write;
- `bend PROOF.bend` — a mechanical gate that fails while laws remain open or false.

This maps naturally to RESIDUAL:

- protected laws -> host-owned acceptance contract;
- candidate Bend code/proofs -> worker output;
- Bend checker result -> one verifier input;
- Station/M4 -> still the authority that decides admission.

Bend proof success must never become a direct integration or merge authority.

## High-value use cases

### 1. Formalizing selected RESIDUAL invariants

Good candidates are pure invariants with compact state spaces or algebraic behavior, for example:

- deterministic state-transition functions;
- capability-set monotonicity properties;
- "routing does not enlarge authority" helper logic;
- receipt/content identity helpers;
- bounded scheduler properties;
- merge/selection functions;
- small policy combinators.

Bend should not initially be used to prove the entire Station or sandbox implementation.

### 2. Proof-backed generated modules

For selected generated components, RESIDUAL could require:

1. protected law file;
2. generated implementation;
3. generated proof;
4. Bend type/proof check;
5. normal RESIDUAL behavioral tests;
6. ordinary receipt/integration gates.

This would make Bend an additional verifier, not a replacement verifier.

### 3. Parallel pure-compute kernels

Bend can target parallel CPU execution and GPU execution. It is most attractive for balanced, independent pure computation.

Potential RESIDUAL workloads include:

- large evidence transforms;
- batch hash-independent analyses;
- matrix/numeric research workloads;
- Monte Carlo / search kernels;
- independent scoring passes;
- synthetic challenge generation;
- selected evaluation aggregation.

It is a poor fit for orchestration-heavy, branch-divergent, IO-heavy Station code.

### 4. Future proof-carrying artifacts

A useful long-term experiment is a candidate artifact that ships:

- source hash;
- law hash;
- proof source hash;
- Bend checker/compiler revision;
- checker result;
- native artifact hash.

RESIDUAL could bind those into a normal evidence receipt.

## Architectural integration point

Use a **separate verifier/engine adapter**, not core changes.

The existing RESIDUAL architecture already expects:

- isolated engine adapters;
- normalized EngineResult output;
- engine-agnostic verification;
- sandbox backends;
- explicit extension registration.

A Bend adapter should therefore run out of process and emit only normalized evidence.

## Proposed boundaries

### BendProofVerifier

Inputs:
- candidate tree;
- pinned Bend binary/toolchain identity;
- protected `LAWS.bend`;
- candidate `PROOF.bend`;
- timeout/resource policy.

Outputs:
- PASS / FAIL / UNKNOWN;
- compiler/checker exit code;
- bounded diagnostics;
- hashes of laws, proof, implementation, and toolchain;
- elapsed/resource data.

A Bend PASS is one verifier result only.

### BendComputeBackend

Optional and later.

Inputs:
- approved Bend source;
- explicitly selected runtime target;
- resource limits;
- deterministic input snapshot.

Outputs:
- result artifact;
- runtime target;
- binary/source hashes;
- execution metrics.

This backend must remain behind RESIDUAL sandbox/resource controls.

## Security and trust concerns

### Compiler maturity

The project states that Bend 2 is young, expects bugs, and that the compiler is largely AI-written and not fully audited.

Therefore:

- do not treat Bend checker success as an ultimate trust root;
- pin exact toolchain versions;
- sandbox checker/compiler execution;
- preserve source + checker output;
- use independent behavioral tests for security-critical claims;
- do not allow foreign imports in the first integration phase.

### Foreign C/JS imports

Bend supports foreign imports. These can bypass the pure-language proof boundary.

Initial RESIDUAL integration SHOULD reject or explicitly quarantine foreign imports unless a separate policy approves them.

### @unsafe

Bend permits `@unsafe` to bypass termination guarantees.

The first proof-verifier profile MUST reject `@unsafe`.

### Proof scope

Bend's proof checker proves the encoded law over the encoded model. It does not prove that:

- the law captures the operator's true intent;
- foreign code is safe;
- IO behavior matches an external system;
- the compiler/runtime implementation has no bugs;
- the generated executable satisfies arbitrary operational security requirements.

RESIDUAL must preserve that claim boundary.

## Performance caveats

Bend's parallel scheduler currently benefits most when calls are independent and similarly sized. Divergent workloads can underperform.

This matters because agent orchestration is often irregular and branch-heavy.

Therefore Bend should not replace Factory scheduling. The value is inside specific computational kernels.

## Current ecosystem limitations relevant to RESIDUAL

Current Bend 2 documentation lists notable constraints:

- no TLS/HTTP/JSON/regex in the standard environment yet;
- one GPU per program;
- no multi-machine execution;
- no incremental/separate native compilation;
- no mature debugger/profiler/LSP/test framework;
- Windows unsupported except WSL;
- compiler/toolchain still young;
- Bend 1/HVM programs do not carry over.

These make Bend unsuitable as a general RESIDUAL application/runtime layer today.

## Integration recommendation

### Phase 0 — no dependency
Keep RESIDUAL main runtime unchanged.

### Phase 1 — proof-verifier experiment
Implement only:
- pinned Bend toolchain discovery;
- isolated Bend proof checker adapter;
- `@unsafe` rejection;
- foreign-import rejection;
- protected law hash;
- normalized verifier evidence;
- deterministic fixtures.

### Phase 2 — qualification
Compare Bend-backed proof checks with existing executable checks on a small set of pure invariants.

Measure:
- checker latency;
- proof authoring/repair attempts;
- false-confidence risks from underspecified laws;
- toolchain instability;
- diagnostics quality;
- model success generating proofs.

### Phase 3 — optional compute benchmark
Only if Phase 1 is stable, benchmark one genuinely parallel pure workload against Python/native baselines.

### Phase 4 — proof-carrying artifact experiment
Bind law/proof/toolchain hashes into Station evidence receipts.

## Go / no-go criteria

Proceed beyond experiment only if:

- checker behavior is stable at a pinned revision;
- RESIDUAL workers can repair proof failures within bounded attempts;
- proof diagnostics materially improve acceptance confidence;
- no authority bypass is introduced;
- sandboxing remains effective;
- maintenance burden is acceptable.

Do not proceed to core dependency if Bend toolchain churn or diagnostics materially reduce reliability.

## Bottom line

Bend is **useful enough to prototype**, primarily because its law/proof workflow matches RESIDUAL's verifier-first philosophy.

Its GPU/parallel runtime is interesting but secondary.

The most valuable first integration is:

**protected law -> AI implementation/proof -> Bend mechanical check -> RESIDUAL verifier/receipt**

not:

**move RESIDUAL execution into Bend**.
