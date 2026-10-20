# Seam DAG — Proposed MS-00…08 Module Boundaries and Dependency Order (G0)

> Status: PROPOSED (docs/tooling only). Derived from the owner directive (2026-09-18, MS-00…08)
> and a re-verified audit of current main. This document is additive; it changes no code semantics.
> Base audited: residual-agent-harness @ `3cff6bcd52e352a6ba048c958949a7bbb2a039eb` (current main HEAD,
> verified via GitHub API). Supersedes the Wave-A draft grounded at `699e2869` (drift corrections noted in §7).
> "MS-00/MS-08/MS-01/MS-02" are owner-directive labels; the mapping below binds each label to seams that exist in current code.

## 1. Seam definitions (mapped to current code)

| Label (directive) | Seam name | Current-code anchor (verified @ 3cff6bcd) | Boundary contract |
|---|---|---|---|
| MS-00 | **Durable ledger core** | `residual/factory/runtime_journal.py` (SQLite WAL `:72`, FULL synchronous `:144`/`:202`, BEGIN IMMEDIATE `:94`/`:204`, hash-chained events with `'GENESIS'` tail `:254`); `residual/dsm/journal.py` (hash chain, `GENESIS = "0"*64` `:15`, startup verify `_load` `:33-40`, seq/prev-hash append `:64`) | Tables, CAS primitives, hash-chained events. Owns no policy. |
| MS-08 | **Admission & fencing** | `residual/dsm/store.py:submit` `:73` (dedupe→ownership→fencing→terminal; commit-before-ack `:108-112`), `residual/dsm/lease.py:LeaseManager` `:17` (monotonic fencing tokens, fail closed), `residual/dsm/ownership.py:TERMINAL_TRANSITIONS` `:21` | Single-writer lease, fencing tokens, idempotent event admission, commit-before-ack. |
| MS-01 | **Lifecycle orchestration** | `residual/factory/runtime.py:FactoryRuntime` `:62` (journal injected `:64`), `residual/factory/worker_contract.py:AttemptGuard` `:216`, `residual/station/service.py:Station` `:70` (owns `Store` `:72`, startup `recover(startup=True)` `:74`) + `residual/station/store.py:transition/claim/recover` `:149`/`:175`/`:204` | Attempt + task state machines; recovery/reconciliation. |
| MS-02 | **Resolution & registry** | `ai_providers/router.py` (bounded failover `_candidates` `:41-42`, one receipt per attempt `_emit` `:34`, fail-closed unknown provider `:20`), `ai_providers/registry.py:get` `:36-47` (unknown provider ⇒ `ProviderError`), `residual/extensions.py:StationExtensionRegistry` `:111`, `residual/station/extensions.py:default_registry` `:19` | Provider resolution/failover receipts; frozen module registry. |

## 2. DAG

Dependency order (a layer may import only from layers at or below itself, plus the shared kernel):

```
 shared kernel: residual.core, observation_layer.*, stdlib   (importable by all; imports no layer*)
 * exception on main: residual.core lazily imports residual.extensions (core.py:240,:271) — see SEAM-GAP-REPORT.md §3.4
                 ┌────────────────────────────┐
                 │ MS-00  Durable ledger core │  layer 0
                 └──────────────▲─────────────┘
                 ┌──────────────┴─────────────┐
                 │ MS-08  Admission & fencing │  layer 1 ┐
                 └──────────────▲─────────────┘          │ parallel:
                 ┌──────────────┴─────────────┐          │ MS-02 depends
                 │ MS-01  Lifecycle           │  layer 2 │ only on kernel
                 │ orchestration              │          │
                 └──────────────▲─────────────┘          │
                 ┌──────────────┴─────────────┐  ◄───────┘
                 │ MS-02  Resolution &        │  layer 1 (consumed BY MS-01)
                 │ registry                   │
                 └────────────────────────────┘
```

Formal rule: **imports flow downward only.** MS-08 and MS-02 are parallel layer-1 seams (neither may import the other); MS-01 may import MS-00, MS-08, and MS-02. Rationale, grounded in current imports:

- MS-08 → MS-00: `dsm/store.py` embeds `dsm/journal.py` (`store.py:50`); fencing without durable storage is the documented DSM gap (`store.py:53` comment re `docs/swarm/dsm-004.md`).
- MS-01 → MS-00/MS-08: `RuntimeJournal` is constructed and passed into `FactoryRuntime` (`runtime.py:62-64`, constructed at `:639`); `Station` owns `Store` (`service.py:72`).
- MS-01 → MS-02: `model_call` / `ai_providers` are consumed from station orchestration (`service.py:14`, `:268`, `:310`, `:384`); the extension registry is built per project (`service.py:79-80`). Resolution serves orchestration, never vice versa (`ai_providers/*` imports no `residual.station`/`dsm`/`factory` module — verified).

## 3. Seam contracts (what crosses each boundary)

| Boundary | Crosses | Must never cross |
|---|---|---|
| kernel/MS-00 → MS-08 | Connection factory, CAS helpers, event append, hash-chain verification | Policy, ownership rules, transition tables |
| MS-00/MS-08 → MS-01 | `submit(event) -> {seq, hash, disposition}`; `lease_read` tri-state (`runtime_journal.py:314`); fencing token issuance (`dsm/lease.py:17`) | Raw connections; uncommitted state |
| MS-02 → MS-01 | `resolve(model, failover) -> plan`; one receipt per attempt (`router.py:34`); registry handle (`extensions.py:111`) | Provider credentials; verifier authority; receipt byte formats |

## 4. Import-layer enforcement (this PR's tooling)

- `.importlinter` — import-linter contracts expressing §2 (layered + forbidden contracts), ready for adoption once import-linter is added as a dev dependency.
- `scripts/check_seam_layers.py` — stdlib-only AST checker expressing the same rules; runs offline today:

  ```
  python3 scripts/check_seam_layers.py
  ```

  Current result @ 3cff6bcd: **1 layer violation, 3 findings** (see SEAM-GAP-REPORT.md §3); import-linter cross-check: **4 contracts kept, 1 broken** (same violation). These are reported as findings for owner decision — this PR deliberately does not restructure code.

CI wire-up (required status check running the script, or `lint-imports` once import-linter is a dev dependency) is a maintainer step: this PR's token lacks `workflow` scope, so no `.github/workflows` change is included.

## 5. Hard boundaries (exclusion boundary restated at the seam level)

- Factory/M4 (`residual/factory/m4_*`), verifier authority (`residual/verifier*`, `verifier/`), receipt serialization, ownership baselines, Evidence Fabric schemas, frozen research definitions: no seam crosses into these; they are consumed as-is. The checker flags any seam-layer import of them as a PROTECTED-IMPORT finding.
- UNKNOWN/BLOCKED never becomes PASS at any seam.
- Multi-host consensus remains outside every seam (DSM's documented deferral, `dsm/store.py:53`).

## 6. Proposed build order (directive-conformant: MS-00/MS-08 → MS-01 → MS-02)

1. **G0:** MS-00 ledger skeleton + MS-08 admission, reusing `residual/dsm/recovery.py` scenarios as the acceptance harness. Exit: crash-between-write-and-ack, restart-mid-stream, replay-determinism proofs; exactly-one-terminal CAS under concurrent writer processes.
2. **G1:** MS-01 reconciliation against G0 ledgers, reproducing `station/store.py:204` `recover` semantics.
3. **MS-02 last:** manifest-hashed registry + resolver receipts wired into MS-01's event chain, preserving `ai_providers/router.py` receipt behavior verbatim.

## 7. Drift corrections vs. the Wave-A draft (@ 699e2869)

Verified against current main; substance unchanged, anchors corrected:

| Draft claim | Status @ 3cff6bcd |
|---|---|
| `runtime.py:63-79` journal injection | holds, now `:62-64` (constructed `:639`) |
| `service.py:51` Station owns Store | holds, now `:72` |
| `service.py:231/273/348` model_call sites | now `:268`, `:310`, `:384` |
| `service.py:62-66` registry build | now `:79-80` |
| Station genesis `'0'*64` (`store.py:93`) | holds, now `store.py:96` |
| DSM genesis `'0'*64` | `dsm/journal.py:15` (confirmed) |
| RuntimeJournal genesis `'GENESIS'` | `runtime_journal.py:254` (confirmed) |
| `runtime_journal.py:371-379` terminal guard | now `finish` `:368-377` |
| `mark_purged` overwrite | now `:384-389` |
| NEW finding | `runtime_journal.py:22` imports `worker_contract` (MS-00 → MS-01 upward import) — the one current layer violation |
| Draft rule "import only layers above it in the drawing" | Corrected: the drawing was ambiguous; §2 states the formal downward-import rule explicitly. MS-02 is parallel to MS-08, not below MS-01. |
