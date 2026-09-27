# SPEC-PROGRAM-CONTROL-001 — RESIDUAL Self-Hosting Program Control

Status: implementation candidate  
Scope: post-v1/self-hosting control layer; MUST NOT expand the admitted v1 execution surface.

## 1. Purpose

RESIDUAL MUST be able to represent, reconcile, prioritize, and evidence-bind its own development backlog without treating repository-open state as authoritative program state.

GitHub remains the source of repository facts (open PRs/issues, PR HEAD/base identity, URLs and timestamps). RESIDUAL owns the normalized program projection: logical state, v1 applicability, workstream, dependencies, supersession, next action, owner gates, and retained program snapshots.

## 2. Controlling invariants

1. **GitHub-open != program-active.** An open PR may be SUPERSEDED, HISTORICAL_EVIDENCE, RESEARCH_ONLY, DEFERRED_POST_V1, or otherwise outside the active critical path.
2. **GitHub disappearance != CLOSED.** Synchronization MUST NOT fabricate closure solely because a PR/issue no longer appears in the open-source inventory.
3. **Authority decisions may be revision-bound.** A HEAD-bound RESIDUAL override MUST become stale and surface HUMAN_ACTION_REQUIRED when the source HEAD changes.
4. **Supersession is explicit.** RESIDUAL may infer supersession only from explicit source wording or a local authority relation. Shared base ancestry alone MUST NOT close or supersede work.
5. **Historical snapshots are immutable.** Every projected snapshot receives a digest and is retained by digest. Program events form a hash chain.
6. **Research does not become v1 implicitly.** Research/post-v1 classification does not confer admission; v1 required/supporting states remain explicit program dispositions.
7. **Owner action is first class.** Items requiring a human ruling/authorization are surfaced independently from ordinary active work.

## 3. Normalized item

Each item contains:

- stable item ID (GitHub PR/issue or local/manual);
- title and source URL;
- exact PR HEAD/base when available;
- state;
- v1 disposition;
- priority and workstream;
- next action and owner-action flag;
- blocked/dependency/supersession/related edges;
- stale-override flag;
- source metadata.

Supported state vocabulary:

DISCOVERED, TRIAGED, READY, RUNNING, VERIFYING, READY_FOR_OWNER_GATE, BLOCKED, HUMAN_ACTION_REQUIRED, DEFERRED_POST_V1, SUPERSEDED, HISTORICAL_EVIDENCE, RESEARCH_ONLY, CLOSED, ABANDONED.

Supported v1 disposition vocabulary:

V1_REQUIRED, V1_SUPPORTING, V1_EXCLUDED, POST_V1, RESEARCH_ONLY, HISTORICAL, UNCLASSIFIED.

## 4. Sources

Initial implementation ingests all open GitHub pull requests and issues. Pull-request shadow rows returned by the GitHub issues endpoint MUST be excluded to prevent double counting.

Non-GitHub work (audit finding, swarm observation, owner decision, external dependency, research gate) is represented by LOCAL-* items.

## 5. Reconciliation

Synchronization performs deterministic normalization and bounded classification. It may propose workstreams/dispositions from explicit wording, but it MUST leave ambiguous work UNCLASSIFIED rather than inventing release authority.

Relations:

- supersedes
- blocked_by
- depends_on
- related

An explicit open successor may project its predecessor to SUPERSEDED. A dependency relation may project ordinary READY/TRIAGED/DISCOVERED work to BLOCKED while the dependency remains active.

Manual authority overrides are persisted separately from GitHub facts and survive synchronization. When an override is HEAD-bound and the PR head changes, it MUST NOT transfer.

## 6. Persistence

Program data lives under the configured Program Control data root.

- current.json — latest projected snapshot
- snapshots/<snapshot_sha256>.json — immutable historical projections
- overrides.json — RESIDUAL-local authority decisions and manual items
- events.jsonl — hash-chained program-control events

inventory_sha256 binds repository, items and relations independently of snapshot timestamp.

## 7. Interfaces

CLI:

- residual program sync
- residual program status
- residual program list
- residual program show
- residual program owner
- residual program set
- residual program link
- residual program add
- residual program export

Station:

- Program Control workspace
- GitHub sync
- snapshot refresh
- owner action queue
- v1 critical/supporting surface
- normalized active inventory
- item detail and bounded state/disposition changes

## 8. Acceptance

The implementation is acceptable when tests prove:

- all open PRs/issues are imported without PR shadow double-counting;
- explicit supersession projects correctly;
- source disappearance does not fabricate a CLOSED record;
- HEAD-bound overrides fail closed when the PR head changes;
- local/manual work can be tracked without GitHub;
- local authority changes project immediately;
- owner action queue and v1 surface are independent of raw GitHub-open state;
- snapshots persist by digest and event history is hash chained;
- Station and CLI surfaces are wired to the same ProgramControl implementation.

## 9. Non-claims

This initial implementation does not autonomously merge PRs, close GitHub issues, approve releases, execute F6, select an RC, or infer that a GitHub workflow PASS closes a program item.

Future work may add workflow ingestion, scheduling, swarm assignment, cost/latency forecasting, program analytics, and autonomous planning only under separate authority rules.
