# AX-21 / R4 Observation — Security Hardening Can Expose Integration Debt Without Weakening the Security Contract

**Observation ID:** AX21-OBS-R4-INTEGDEBT-20260925-004  
**Date:** 2026-09-25  
**Status:** OBSERVED / CORPUS EVIDENCE  
**Campaign:** SNYK-R4-02  
**PR:** #457 (draft)

## Exact-head sequence

- Original security remediation: `ff410b5fb8695104f1dc78ffae7cc78199e15da9`
- Integration successor: `2b75b42cd8cf1a7f13eac64a77d86ddfb619d169`
- Successor tree: `82ffc85b5d7611b08c9cc9c16ba2bebfc5604f14`

The original security head tightened the supported Python security floor. Exact-head CI then exposed lifecycle and VM environments below that floor. The successor reconciled those environments without weakening the security requirement.

## Observed reconciliation

The campaign classified 79 runtime entries and converged the relevant environments to:

- Windows lifecycle: Python 3.13.15
- macOS lifecycle: Python 3.13.15
- Pages VM: Python 3.11.16 on Bookworm linux/386
- preserved Ollama container: patched Python 3.12.14

Final non-evidence changes were limited to one workflow and two Dockerfiles.

## Exact-head result

At successor head `2b75b42c...`:

- Qualification-v1: PASS, 25/25 required gates.
- M4: PASS.
- Windows lifecycle: PASS.
- macOS lifecycle: PASS.
- Pages VM: PASS, including image execution and desktop/narrow browser proofs.
- Deterministic regression: 2,406 JUnit cases, zero failures/skips.
- Archive security tests included: 83.
- Candidate failures: none.
- Environment failures: none in final CI.
- Security floor weakened: no.
- PR-Agent advisory remained a separate external-automation failure.
- PR remained draft; merge remained unauthorized.

## Candidate invariant

**AX21-SEC-INTEG-01 — Security Contract Dominates Integration Convenience**

> When a security hardening change invalidates dependent execution environments, convergence should update those environments to satisfy the security contract rather than silently weaken the contract to preserve stale compatibility, unless an explicitly reviewed equivalent protection is provided.

## Why this matters

The first exact-head run was not evidence that the archive remediation should be relaxed. It was evidence that parts of the qualification infrastructure encoded obsolete runtime assumptions.

The successful successor demonstrates a useful convergence pattern:

```
security invariant strengthened
        ↓
integration incompatibility exposed
        ↓
runtime inventory / classification
        ↓
dependent environments upgraded
        ↓
fresh exact-head qualification
        ↓
security invariant preserved + integration restored
```

This separates **security regression** from **integration debt revealed by security hardening**.

## Candidate orchestration rule

When a new invariant causes downstream failures:

1. preserve the original security evidence head;
2. classify each failure domain;
3. test whether the invariant itself failed;
4. inventory dependent environment assumptions;
5. prefer environment reconciliation over security relaxation;
6. create a separate successor commit;
7. rerun exact-head qualification;
8. retain both pre- and post-reconciliation receipts.

## Research implications

- Runtime/version selection is part of the effective security architecture.
- Qualification infrastructure can contain latent compatibility debt invisible until a security floor becomes explicit.
- Exact-head provenance allows the security fix and integration reconciliation to remain independently reviewable.
- A fully green matrix is meaningful only when the path to green did not weaken the tested invariant.
- External advisory automation should remain a distinct evidence domain rather than contaminating candidate correctness.

## Follow-up experiment

Generalize the pattern to other security contracts (browser origin policy, network destination confinement, plugin filesystem roots). Deliberately tighten one contract in a controlled branch, enumerate downstream compatibility failures, and compare two convergence strategies:

A. weaken the security invariant;
B. update dependent environments/interfaces.

Measure which strategy preserves the original adversarial oracle while restoring qualification.

## Limitations

This observation is scoped to the reported PR #457 exact-head sequence and runtime matrix. It does not itself constitute independent review or merge authorization. The PR-Agent advisory failure remained unresolved at the time of this observation.
