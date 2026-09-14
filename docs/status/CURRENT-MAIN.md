# Current Main Snapshot

This file is a short human-readable companion to the generated implementation-status report. It exists because the repository is currently merging large parallel work streams faster than the generated family manifest is always refreshed.

## Current merged state

As of the latest merged swarm acceptance evidence on `main`:

- Factory requirement compilation and exact plan approval are present.
- Factory M2 worker execution is present under `residual/factory/`, including bounded Linux worker isolation, worktrees, private candidate object stores, brokered file access, durable attempt journals, leases, cancellation, and quarantine.
- Factory M3 trusted evidence is present under `residual/factory/`, including Station signing, worker receipts, content-addressed accepted artifacts, evidence storage, and receipt-based dependency admission.
- Adaptive assurance primitives are present for verifier quality, orchestration tax, heterogeneous compute selection, authority/quorum boundaries, and assurance receipts.
- The broader swarm buildout includes sandbox/red-team, cluster, orchestration, evaluation/soak, gateway/lifecycle, crypto, connector conformance, Studio frontend, onboarding, and status/traceability paths.
- `verifier/v3/check_swarm.py` is the current repository-level swarm acceptance check.

## Latest retained acceptance evidence

The latest retained merged-tree verifier record reports:

- `pytest`: **1033 passed**
- additional subtests: **166 passed**
- earlier verifier v2: **green**
- protected Factory-owned paths: **untouched by unrelated swarm tracks**

See `verifier/runs/2026-09-14T06-v3-pass-merged-with-factory.txt` and `verifier/v3/check_swarm.py`.

## Important boundary

This snapshot describes what is merged, not what every open PR proposes. Active swarm research PRs may contain stronger evaluation, verifier-quality, orchestration, distributed-state, runtime, or observability implementations that are not yet part of `main`.

For exact behavior, use this precedence:

1. current source;
2. current tests;
3. component implementation docs;
4. retained verifier evidence;
5. generated status prose.

`docs/status/IMPLEMENTATION_STATUS.md` remains generated from `implementation-status.yaml` and should not be edited by hand.