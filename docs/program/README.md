# RESIDUAL Program Control

`SPEC-PROGRAM-CONTROL-001` defines the authority model. This page is the operator quickstart.

Program Control is a **self-hosting/post-v1 control layer**. It does not expand the v1 supported execution surface, authorize merge/release actions, or convert GitHub CI results into acceptance.

## What it tracks

The first implementation imports every open GitHub pull request and issue, then overlays RESIDUAL-owned program state:

- v1 applicability;
- logical workstream;
- priority;
- blockers and dependencies;
- explicit supersession;
- next action;
- owner-action gates;
- manual/audit/research items that do not belong in GitHub.

GitHub remains observational input. RESIDUAL owns the normalized projection.

## First bootstrap

From a checkout containing Program Control:

```bash
residual program sync --repo ninja-ops-guy/residual-agent-harness
residual program seed docs/program/RESIDUAL_SELF_HOSTING_SEED.json
residual program status
residual program owner
```

The seed records the known 2026-09-27 v1/post-v1 dispositions and successor relations. Active PR decisions are bound to the PR HEAD present when the seed is applied. If that HEAD later moves, the decision becomes stale and Program Control surfaces `HUMAN_ACTION_REQUIRED` instead of transferring it.

If GitHub authentication is needed, set `GITHUB_TOKEN` in the process environment. The token is used only for GitHub API requests and is not written into Program Control snapshots.

## Common commands

Show active normalized work:

```bash
residual program list
```

Show the v1/owner summary as JSON:

```bash
residual program status --json
residual program owner --json
```

Inspect one item:

```bash
residual program show GH-PR-0478 --json
```

Make an explicit HEAD-bound program decision:

```bash
residual program set GH-PR-0478 \
  --state READY_FOR_OWNER_GATE \
  --disposition V1_REQUIRED \
  --priority P0 \
  --owner-action yes \
  --next-action "Perform exact-head owner review" \
  --bind-current-head
```

Add a non-GitHub owner gate:

```bash
residual program add "Owner disposition: D4 Shared Comms" \
  --state HUMAN_ACTION_REQUIRED \
  --disposition V1_REQUIRED \
  --workstream RELEASE_CONTROL \
  --priority P0 \
  --next-action "Record INCLUDE or EXCLUDE" \
  --owner-action
```

Record explicit relationships:

```bash
residual program link GH-PR-0478 supersedes GH-PR-0428
residual program link GH-PR-0483 depends_on GH-PR-0476
```

Re-sync GitHub at any time:

```bash
residual program sync
```

A source item that disappears from GitHub's open inventory is **not** silently closed. RESIDUAL carries it forward as `HUMAN_ACTION_REQUIRED` until the merge/closure is explicitly reconciled.

## Command Station

Run the Station normally:

```bash
residual serve --open
```

Open **Program control** in the sidebar. The view shows:

- tracked and active counts;
- owner action queue;
- v1 required/supporting surface;
- unclassified work;
- active workstreams;
- normalized active inventory;
- exact source identity for revisioned PRs;
- stale authority warnings.

Program-state changes made through Station are written through the same `ProgramControl` implementation as the CLI.

## Persistence and evidence

Default CLI data root:

```text
~/.residual/program/
```

Station uses:

```text
<station-data>/program-control/
```

Each contains:

```text
current.json
overrides.json
events.jsonl
snapshots/<snapshot_sha256>.json
```

`events.jsonl` is hash chained. Historical snapshots are retained by digest. `inventory_sha256` binds the repository/items/relations projection independently of the wall-clock snapshot timestamp.

## Deliberate non-automation

Program Control does **not** currently:

- merge or close GitHub objects;
- approve a PR;
- infer program closure from a workflow PASS;
- execute F6/canary/deployment/soak;
- select or tag an RC;
- mutate source branches;
- silently transfer an owner decision to a new PR HEAD.

Those actions remain behind their existing authority gates.
