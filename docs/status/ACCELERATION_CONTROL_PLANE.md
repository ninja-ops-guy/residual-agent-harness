# RESIDUAL Acceleration Control Plane

Status: implementation candidate  
Scope: release/research portfolio orchestration  
Authority: advisory only; never grants execution, merge, release, or research-claim authority

## Purpose

The acceleration control plane reduces elapsed time by removing avoidable human coordination
and idle dependency gaps without weakening RESIDUAL's existing authority model.

It operates **above** Factory/M4. Factory remains authoritative for task-level scheduling,
receipt-backed completion, and deterministic integration. This layer only answers:

1. What work is executable now?
2. What future work can be safely prepared without crossing a dependency gate?
3. What work is frozen by the v1 release boundary?
4. Which human authorization items are actually ready for an owner decision?
5. What is the state and benefit of each research/release lane?

## Non-goals

This component MUST NOT:

- auto-approve a human gate;
- infer success from model confidence;
- override M4 dependency receipts;
- mutate protected branches;
- convert research preparation into execution authority;
- treat an incomplete review package as owner-ready.

## Manifest

A manifest has four top-level fields:

- `schema_version = residual-acceleration-control-plane-v1`
- `release_freeze`
- `lanes[]`
- `tasks[]`

Task scopes are:

- `required` — may execute while the v1 release freeze is active;
- `post_v1` — execution is frozen until the release freeze clears;
- `research` — execution is frozen until the release freeze clears.

A non-required task may still become `prep_ready` when `preparable=true`. Prep readiness
does not imply permission to execute the dependent experiment or integration.

## Human gate compression

A `human_gate` task requires an `owner_action` package. It enters the owner queue only when:

- every dependency is complete;
- release scope permits the action;
- required checks passed;
- independent review passed;
- unresolved findings equals zero;
- an exact evidence digest and copyable approval string are present.

Otherwise it remains fail-closed as `owner_blocked`, `blocked`, or `frozen`.

## CLI

```bash
residual ops validate examples/acceleration-control-plane.example.json
residual ops status examples/acceleration-control-plane.example.json
residual ops ready examples/acceleration-control-plane.example.json
residual ops owner-queue examples/acceleration-control-plane.example.json
```

The same implementation is also directly invokable as:

```bash
python -m residual.control_plane.accelerator_cli status <manifest.json>
```

## Intended timeline effect

The acceleration layer attacks four forms of latency:

- **owner archaeology** → exact owner queue with evidence binding and copyable action;
- **dependency idle time** → explicit speculative-preparation state;
- **scope creep** → machine-enforced v1 freeze;
- **status synthesis** → deterministic per-lane snapshot.

The target metric is not raw agent count. It is:

`verified useful work / operator active minute`

A useful follow-on experiment is to compare this metric before and after the acceleration
control plane is adopted, while holding task mix and verification requirements constant.
