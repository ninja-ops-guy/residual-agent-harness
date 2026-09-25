# AX-21 / R4 Observation — Security Equivalence Requires Authority Equivalence

**Observation ID:** AX21-OBS-R4-ARCHIVE-20260925-002  
**Date:** 2026-09-25  
**Status:** OBSERVED / CORPUS EVIDENCE  
**Campaign:** SNYK-R4-02  
**Scope:** runtime archive extraction authority

## Observation

Three functionally equivalent runtime-install paths used materially different protection authorities:

- TAR: Python `tarfile` data-filter behavior plus explicit RESIDUAL validation after remediation.
- ZIP: RESIDUAL-owned member-path/type validation.
- TAR.ZST pre-fix: external GNU tar behavior after decompression support was delegated to the tool.

The pre-fix adversarial matrix showed that passing ordinary tests and preventing immediate outside writes were insufficient security predicates. Two TAR.ZST fixtures created outside-pointing symlink authority even though extraction itself did not directly modify the outside sentinel.

The stronger oracle tested **authority creation**, not only immediate effects.

## Empirical result

Pre-fix:
- 42 real extraction cases.
- Existing security suite: 36 passing tests.
- TAR.ZST `symlink_alone`: outside authority created.
- TAR.ZST `symlink_then_file`: outside authority created even though later extraction failed.
- Bounded follow-up probes verified that both retained symlinks could write outside the intended extraction root.
- Pinned manifest SHA-256 remained a separate trust boundary; the experiment supplied digest-matched malicious bytes and did not demonstrate a digest bypass.

Post-fix:
- TAR.ZST is decompressed to TAR and routed through the common validated TAR path.
- Extraction occurs in disposable staging.
- Member and link targets are explicitly validated.
- The staged tree is post-validated before promotion.
- Failed extraction does not promote partial runtime state.
- Post-fix matrix: 36 BLOCKED, 6 ALLOWED_BUT_CONFINED, zero newly created outside authority and zero extraction-time outside writes.
- Targeted archive tests: 83 passed.
- Station tests: 37 passed.
- Sensitivity tests killed the frozen pre-fix behavior and mutants removing link validation or staging cleanup.
- Active-workload and exact-wheel checks passed.
- Full deterministic qualification remained blocked by a host M4 namespace/mount environment failure; this observation does not convert that blocked gate into a pass.

## Candidate invariant

**AX21-AUTH-EQUIV-01 — Authority Equivalence Across Implementations**

> Two implementations that provide the same functional capability are not security-equivalent unless they enforce the same authority boundary. Qualification must test the authority that remains after an operation, including partial-failure state, rather than only immediate side effects or return status.

## Candidate verifier rule

For filesystem-producing operations, a successful security predicate should consider at least:

```
immediate_outside_write == false
AND
new_outside_authority == false
AND
failed_operation_promoted_state == false
AND
retained_state_passes_confinement_validation
```

An exception or nonzero return code alone is not proof of containment.

## Research implications

1. **Security semantics should be normalized above implementation choice.** TAR, ZIP, external tools, provider SDKs, or platform-specific implementations should satisfy one authority contract even when their mechanisms differ.
2. **Failure state is part of the attack surface.** A failed operation can still leave durable capability behind.
3. **Green tests can miss the wrong oracle.** The pre-fix suite passed while checking absence of an outside marker; the stronger authority oracle found retained capability.
4. **Negative controls should prove oracle sensitivity.** Unsafe controls demonstrated traversal/authority creation, and mutation tests proved the remediated tests detect removal of critical controls.
5. **Environment failures must remain separate from product findings.** Local M4 qualification failures were retained as blockers rather than being laundered into a product-security pass or failure.

## Follow-up experiment

Generalize the authority oracle beyond archive extraction:

- network operations: final destination authority after redirects;
- worker leases: authority remaining after timeout/reassignment;
- filesystem plugins: authority remaining after failed installation;
- browser messaging: authority of sender/source after message parsing;
- evidence systems: authority implied by retained identity assertions versus recomputed identity.

For each domain, compare an effect-only oracle against an authority-aware oracle and measure whether the latter discovers violations missed by the former.

## Limitations

This observation is grounded in the recorded Linux/WSL2 R4-02 experiment and its bounded archive fixtures. It does not establish universal archive safety, native Windows/macOS behavior, or full release qualification. The production manifest digest was not bypassed.
