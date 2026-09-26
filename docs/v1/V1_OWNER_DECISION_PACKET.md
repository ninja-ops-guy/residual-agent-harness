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

Choose one:

- D1-A — container is supported in v1. Define the protected ingress contract, repair default startup in a successor to #448, add a real startup test, and requalify before physical F6.
- D1-B — container is excluded from v1. State the exclusion explicitly in the release matrix and public claims.

Do not weaken `validate_exposure()` merely to make the image start.

## D2 — Distribution license

Current repository observations:

- no root `LICENSE` or `COPYING` file exists on observed main;
- `pyproject.toml` declares no project license metadata;
- `docs/enterprise/commercial/licensing.md` says the core uses a free, permissive license;
- commercial licensing/enforcement concepts also exist.

Before public v1 distribution, select and record the actual source/distribution terms. This packet does not select legal terms.

After the choice:
1. add authoritative root license text;
2. add package metadata;
3. reconcile README/docs;
4. identify third-party notices/attributions;
5. bind license files into release artifacts.

## D3 — Supported release matrix

Approve an exact initial support matrix before final dependency locking and RC qualification, including:
- OS families;
- architectures;
- Python patch-level floors;
- native versus Docker support;
- browser/WebVM claim scope;
- local Ollama scope;
- cloud/live-provider claims included or explicitly UNKNOWN/out-of-scope.

The matrix becomes an input to clean-install, reproducibility, recovery and soak evidence. Do not infer support merely from incidental CI runners.

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
D1_CONTAINER_SUPPORT: A_SUPPORTED | B_EXCLUDED | UNDECIDED
D2_DISTRIBUTION_LICENSE: <selected terms or UNDECIDED>
D3_RELEASE_MATRIX: <approved matrix reference or UNDECIDED>
D4_SHARED_COMMS_V1: INCLUDED | EXCLUDED_BY_DEFAULT | UNDECIDED
D5_RC_OPERATIONS_PROFILE: <approved profile/reference or UNDECIDED>
```

Until required decisions are recorded, this document does not authorize RC creation or release.
