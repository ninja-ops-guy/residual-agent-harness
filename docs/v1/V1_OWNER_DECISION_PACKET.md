# RESIDUAL v1 — owner decision packet

Purpose: collect the remaining choices that cannot be resolved by additional CI alone.
Boundary: this document records decision inputs; it does not make the decisions or authorize release.

## D1 — Container support in v1

Observed #448 candidate behavior:

- Station defaults to fail-closed loopback exposure.
- Dockerfile starts Station with `--host 0.0.0.0`.
- hardened Station rejects non-loopback binds without explicit protected-exposure policy.
- Compose publishes host `127.0.0.1:8765` but does not supply the required Station exposure policy.
- current Docker CI overrides the image entrypoint, so it does not test default startup.

Decision recorded 2026-09-25: **D1-A — container is supported in v1.** A dedicated successor to #448 must define and qualify the protected local-container ingress contract before physical F6.

Do not weaken `validate_exposure()` merely to make the image start.

## D2 — Distribution license

The project direction is already selected: **Apache-2.0 Open Core with reserved/proprietary commercial and enterprise layers**.

Current GitHub reconciliation shows the legal boundary work in #391 and the narrower #442 candidate. #442 contains Apache-2.0 license material, an explicit open-source manifest/exporter, and reserved commercial boundaries, but remains open/unmerged. The GitHub installation visible to this convergence lane does not expose a separate RESIDUAL commercial/enterprise repository, so existence and license state of that repository cannot be treated as independently verified here.

This is therefore no longer a "choose a license model" decision. The remaining release work is implementation/provenance reconciliation:

1. accept the final open-core boundary (#442 or its reviewed successor);
2. ensure the exported/public v1 artifact carries the Apache-2.0 grant and NOTICE/attribution material;
3. verify reserved/commercial implementation is not accidentally included in the open-core release artifact;
4. record the separately controlled commercial repository identity and its license terms in the private/commercial release ledger;
5. bind the public artifact's license manifest into SBOM/provenance/release receipts.

No commercial source needs to be published merely to satisfy this gate.

## D3 — Supported release matrix

Decision recorded 2026-09-26 in `docs/v1/V1_RELEASE_MATRIX.md`.

v1 scope:
- native Windows x64 and Linux x64;
- Docker local-workstation on Linux Docker Engine and Docker Desktop Windows;
- NVIDIA Compose overlay;
- desktop Chromium, Firefox and automated WebKit browser contracts;
- local Ollama;
- at least one real hosted-provider end-to-end success.

Held for v2:
- native macOS x64 and ARM64;
- Docker Desktop macOS.

Physical iPhone heavyweight WebVM is explicitly unsupported in v1.

Remaining D3 sub-decision: name the hosted provider/model or deployment target(s) whose real candidate -> verifier -> receipt success will satisfy the hosted-provider release gate.

## D4 — Shared Comms relationship to v1

Default convergence boundary:
- #400/#404/SC-MESH/AX-21 remain separate integration/research work;
- they may feed bounded evidence into Convergence;
- they enter v1 only if required to repair a demonstrated existing v1 invariant.

Confirm this boundary so Shared Comms work cannot move the RC target implicitly.

## D5 — Exact-RC operational acceptance

After convergence produces one exact RC SHA, approve the operational evidence window:
- clean install;
- backup/restore;
- upgrade/rollback if claimed;
- host/process restart recovery;
- incident/diagnostic procedure;
- elapsed soak duration;
- storage/disk budget;
- evidence retention period;
- named release/incident owner.

These must be performed against the exact RC artifact rather than inherited from predecessor PR heads.

## Decision record

```text
D1_CONTAINER_SUPPORT: A_SUPPORTED
D2_DISTRIBUTION_LICENSE: APACHE-2.0 OPEN CORE + RESERVED/PROPRIETARY COMMERCIAL LAYERS — implementation/repository verification pending
D3_RELEASE_MATRIX: docs/v1/V1_RELEASE_MATRIX.md
D4_SHARED_COMMS_V1: INCLUDED | EXCLUDED_BY_DEFAULT | UNDECIDED
D5_RC_OPERATIONS_PROFILE: <approved profile/reference or UNDECIDED>
```

Until required decisions are recorded, this document does not authorize RC creation or release.
