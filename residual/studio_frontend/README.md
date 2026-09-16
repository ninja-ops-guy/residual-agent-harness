# Residual Studio frontend (Track H, stub API)

A self-contained, no-build-step Studio UI (HTML/CSS/JS) plus a stdlib-only
stub API server that serves the M2 swarm contract shape defined in
`docs/studio/STUDIO_SPECS.md`.

## Surfaces

- **Requirement graph** — interactive SVG DAG of the compiled
  `RequirementGraph` with acceptance criteria, provenance spans, risk flags,
  and the critical path highlighted (STUDIO-R5, R7).
- **Swarm panel** — per-swarm workers, ready/blocked counts, critical path,
  effective speedup, coordination overhead, rework rate, verifier rejection
  rate, and cluster node capacity (STUDIO-R25, R33).
- **Evidence graph** — append-only `WorkerReceipt` table binding task,
  attempt, engine/node identity, artifact hashes, requirement verdicts,
  verification results, parent receipts, and supersession (STUDIO-R11, R18).
- **Worker timeline** — per-worker attempt spans over the run window.
- **Approvals** — HITL plan/retry gates; decisions POST back to the stub and
  bind the exact subject hash (STUDIO-R7, R8).

## Launch

```bash
python3 -m residual.studio_frontend.stub_server --port 8787
# open http://127.0.0.1:8787/
```

## Contract stubs

`contracts.py` mirrors the normative `WorkerContract` / `WorkerReceipt`
shapes (SPEC-STUDIO-003). These are local stubs required by the swarm
ownership rule: `residual/swarm/**` is owned by the M2–M4 effort and MUST NOT
be imported or modified here. When the real runtime lands, replace the stubs
with the real types and keep the JSON wire shape unchanged.

Fixtures in `fixtures/` are validated against the stub dataclasses at server
start; approval decisions are in-memory only and reset on restart.
