# RESIDUAL v1 readiness audit — append-only reconciliation delta

**Date:** 2026-09-25  
**Observed main:** `d796f36b75e730a0bab71bdba564206174393719`  
**Purpose:** reconcile later exact-head evidence against the previously preserved v1 readiness audit without rewriting historical findings.

This document is a delta only. Earlier audit statements remain historical evidence for the exact heads they described.

## 1. Exact-head reconciliation

| Work item | Current exact head | Reconciled state |
|---|---|---|
| #448 CV-06 / AUD-1 product candidate | `943c77a28ada1bc3931408c5f9b40d40c25eb2dc` | Frozen technical candidate; physical F6 still not executed |
| #455 F6 evidence helper | `a2567103c7e634310d696e421692fa1f86624e3b` | Qualification-v1 and substantive technical workflows PASS; exact-head maintainer approval observed; physical F6 remains a separate gate |
| #458 R4-02 B1 successor | `e8894c443936710b86efc85e9cbcc29a5f70840e` | Qualification-v1 and substantive workflows PASS; B1 base/candidate adversarial oracle and mutation sensitivity reported PASS; final independent disposition remains required |
| #459 automation tooling | `e16fa5e56db4688846f5b185a513b406f4ca5523` | Qualification-v1 and substantive workflows PASS; automation is support tooling only and carries no release authority |
| #429 version metadata | `9d38d87df9bfa5004d3eb5d7144e60ef1ced56f7` | Still open; final version/release normalization remains a convergence task |
| #440 Action pinning | `72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce` | Top-level selected action pins correspond to observed upstream refs; F03-YAML-01 and transitive mutable inputs remain separate findings |
| #464 structural Action-pin successor | `592f184f95224bff0e31691559bbb452ded2aebd` | Draft successor for F03-YAML-01; structural YAML parsing and supplemental regressions added; exact-head CI required |

## 2. Superseded audit statements

The following prior statements are no longer current truth, while remaining valid historical observations:

- "#458 corrected successor required" — superseded by #458 itself at `e8894c44...`, which is the promotion-invariant B1 successor.
- "#455 helper-integrity findings remain OPEN" — materially advanced by helper hardening, exact-head technical PASS, and maintainer attestation. Physical F6 and independent post-F6 adjudication remain open.
- "P3.3 CONTRACT_ONLY / NOT_EXECUTION_VERIFIED" — later live evidence has observed process replacement and semantic configuration continuity. Final controlled fallback/restore/replay receipt is still required before closure.

## 3. Confirmed open code/integration blockers

### 3.1 Docker default startup versus non-loopback exposure policy

At #448 the Dockerfile defaults to:

```
python3 -m residual.station.server --host 0.0.0.0 --port 8765 --start-ollama
```

The hardened Station rejects a non-loopback bind unless explicit remote-exposure policy is supplied. The Compose service publishes the container port only to host loopback, but does not supply the policy values the server currently requires. The Docker CI job overrides the image entrypoint and therefore does not exercise documented/default Station startup.

**Disposition:** OPEN pending an explicit supported-container deployment decision and a tested startup contract. Do not weaken the exposure guard merely to make the image start.

### 3.2 GitHub Action structural audit

#440's original line-oriented Action pin scanner has a reproduced false-PASS/false-positive parsing defect (F03-YAML-01).

Draft #464 addresses this narrowly through structural YAML-node parsing, rejects ambiguous YAML constructs, binds pin-set checking to the same parser, and explicitly provisions the existing qualification dependency `PyYAML==6.0.3`.

**Disposition:** OPEN until #464 exact-head CI and review complete.

### 3.3 Transitive mutable supply-chain inputs

Top-level 40-hex Action pins do not establish transitive closure. The following source-confirmed inputs remain unresolved:

- `actions/upload-pages-artifact` contains a nested mutable `actions/upload-artifact@v4` reference.
- the pinned PR-Agent action ultimately selects mutable image `pragent/pr-agent:github_action`.

These are not evidence of compromise. They are unresolved reproducibility/provenance inputs.

## 4. Qualification blockers that remain

- Physical F6-A/F6-B has not been executed against the accepted exact product/helper identities.
- Independent post-F6 reconciliation/adjudication is absent.
- No converged release tree has been assembled from the accepted successor set.
- Fresh full qualification on the resulting converged tree is absent.
- Final supported platform/artifact matrix remains an owner decision.
- Exact-RC install, recovery, rollback, and elapsed-soak evidence remains a later release gate.

## 5. Scope boundary for Shared Comms

SPEC-SC-MESH-001 / #404, legacy OC-BRIDGE-R0 / #400, AX-21 and live swarm recovery operate in a separate integration/research lane by default.

Evidence crosses into v1 convergence only when it demonstrates violation of an already accepted v1 invariant. The default handoff is:

```
Shared Comms / AX-21
        |
        v
bounded evidence or candidate patch
        |
        v
Convergence admission decision
```

Shared Comms work does not opportunistically move the frozen v1 candidate.

## 6. Current shortest path to first RC

1. Complete #458 independent exact-head security disposition.
2. Complete #464 structural-action-audit qualification/review and separately disposition #440 transitive supply-chain inputs.
3. Resolve or explicitly exclude the Docker/container startup contract through the approved release matrix.
4. Execute separately authorized physical F6 using the qualified helper, then obtain independent adjudication.
5. Select the accepted successor set and build one converged release tree.
6. Run fresh full Qualification-v1 and surrounding release/security gates against that exact tree.
7. Reconcile versions, changelog, build inputs, platform/artifact matrix and release receipt.
8. Explicitly authorize the RC.
9. Run exact-RC install/recovery/rollback/soak evidence before final release disposition.

## 7. Current RC disposition

```
V1_RELEASE_CANDIDATE_CAN_BE_CUT_NOW: NO
PHYSICAL_F6_STATUS: NOT_EXECUTED
CONVERGED_RELEASE_TREE: ABSENT
KNOWN_RELEASE_BLOCKERS: NONZERO
```

This delta does not authorize merge, physical F6, RC creation or release.
