# Seam Gap Report — Current Code vs. Proposed MS-00…08 Seams (G0)

> Additive analysis only. Base: residual-agent-harness @ `3cff6bcd52e352a6ba048c958949a7bbb2a039eb`
> (current main HEAD, verified via GitHub API, 2026-09-18). Re-verifies and corrects the Wave-A
> gap notes grounded at `699e2869`. Every item states EXISTS / PARTIAL / MISSING / VIOLATES with citations.

## 1. Seam existence summary

| Proposed seam | Exists today? | Evidence |
|---|---|---|
| MS-00 durable ledger core | **PARTIAL** — two ledger implementations exist, no unified core | `residual/factory/runtime_journal.py` (SQLite, WAL `:72`, FULL sync `:144`/`:202`, hash chain `:254`); `residual/dsm/journal.py` (JSONL file, hash chain `:15`/`:33-40`); `residual/station/store.py` events table (`:44`, genesis `"0"*64` `:96`) — three stores, three chain formats |
| MS-08 admission & fencing | **PARTIAL** — full admission pipeline exists in DSM; not shared with factory/station writers | `residual/dsm/store.py:submit` `:73` (dedupe → ownership → fencing → terminal, commit-before-ack `:108-112`); `residual/dsm/lease.py:LeaseManager` `:17`; `residual/dsm/ownership.py:TERMINAL_TRANSITIONS` `:21`. Lease table intentionally in-memory pending consensus (`store.py:53`, `docs/swarm/dsm-004.md`) |
| MS-01 lifecycle orchestration | **EXISTS** | `residual/factory/runtime.py:FactoryRuntime` `:62`; `residual/factory/worker_contract.py:AttemptGuard` `:216`; `residual/station/service.py:Station` `:70` + `residual/station/store.py:transition/claim/recover` `:149`/`:175`/`:204` |
| MS-02 resolution & registry | **EXISTS (resolution) / PARTIAL (registry)** | `ai_providers/router.py` (bounded failover `:41-42`, per-attempt receipts `:34`, fail-closed unknown provider `:20`); `ai_providers/registry.py:get` `:36-47`; `residual/extensions.py:StationExtensionRegistry` `:111`. Registry is programmatic — no declarative manifest or manifest hash on main |
| Import layering as DAG | **MISSING (new)** | No layering rules existed; this PR adds `.importlinter` + `scripts/check_seam_layers.py` |

## 2. Behavioral gaps (carried from Wave-A, re-verified @ 3cff6bcd)

- **EXACTLY-ONE-TERMINAL rests on deployment discipline, not storage.** `RuntimeJournal.finish` is SELECT-then-UPDATE (`runtime_journal.py:368-377`), correct only under a single writer process; `started()` is a true rowcount CAS (`:294-300`). The proposed seam closes this with `terminal_state IS NULL` predicates + unique indexes. UNCHANGED since `699e2869`.
- **Three genesis/chain formats.** DSM `GENESIS = "0"*64` (`dsm/journal.py:15`), Station `"0"*64` (`station/store.py:96`), RuntimeJournal `'GENESIS'` (`runtime_journal.py:254`). Unification needs an owner migration decision — flagged, not resolved.
- **`mark_purged` overwrites terminal state** with `'PURGED'` (`runtime_journal.py:384-389`), erasing the original terminal value from the row (event log retains it). UNCHANGED.
- **No cross-restart attempt reconciliation in factory.** Rows left `RESERVED`/`RUNNING` by a dead run persist; liveness is per-run watchdog/reap only (`runtime.py`). Station startup recovery does exist (`station/store.py:204-219`, invoked `service.py:74`). UNCHANGED.
- **Station task leases have no fencing tokens** — safety today rests on single-writer atomic claim overwrite (`station/store.py:155`, `:175-190`). Proposed seam adds fencing so it stays safe under a writer-service model. UNCHANGED.
- **No durable resolution-plan record** — receipts go to the observation bus only (`ai_providers/router.py:34`); bus failures are counted, not fatal. Additive ledger provenance proposed; routing correctness does not depend on it. UNCHANGED.

## 3. Import-layer findings (checker output @ 3cff6bcd)

`python3 scripts/check_seam_layers.py` → **1 violation, 3 findings** (exit 1).
Cross-checked with real import-linter (`lint-imports --config .importlinter`, import-linter installed locally):
**4 contracts kept, 1 broken** — the broken contract is the same single violation below; both tools agree.

1. **LAYER-VIOLATION (MS-00 → MS-01):** `residual/factory/runtime_journal.py:22` imports `WorkerContract, WorkerContractError` from `residual.factory.worker_contract` (import-linter confirms: `runtime_journal -> worker_contract (l.22)`). The ledger core's API is typed on the orchestration layer's contract object (used at `:263`, `:294`, `:304`, `:314`, `:355`, `:368`). Options for the owner (NOT done here): (a) move `WorkerContract` to a kernel/contracts module; (b) re-type the journal API on primitive fields; (c) record an explicit exemption. This must be resolved or exempted before CI gating is adopted.
2. **PROTECTED-IMPORT finding:** `residual/extensions.py` (MS-02) imports `residual.verifier`.
3. **PROTECTED-IMPORT finding:** `residual/station/extensions.py` (MS-01) imports `residual.verifier`.
4. **KERNEL-IMPORT finding:** `residual/core.py` (shared kernel) lazily imports `residual.extensions` (`VerifierRevision`) at `:240` and `:271`, deferred inside function bodies — a kernel → MS-02 upward edge, meaning the "kernel imports no layer" ideal does not fully hold today. Exempted in `.importlinter` with an inline comment pending owner decision.

Findings 2–3 are consumption-as-is of verifier authority (permitted by the exclusion boundary: seams must not *modify* verifier authority). They are reported so the owner can decide whether resolution/orchestration should reach verifier internals directly or via a narrow interface.

Everything else conforms: `ai_providers/*` imports no `residual.station`/`dsm`/`factory` module; `residual.dsm/*` imports no upper layer; `residual.factory/runtime.py` imports only the kernel (`residual.core`, `:26`) plus its own layer; `observation_layer/*` imports no seam layer.

## 4. Open questions for the owner (not silently resolved)

1. Resolve or exempt the `runtime_journal → worker_contract` upward import before CI gating (§3.1).
2. Migrate or abandon existing per-run RuntimeJournal files when unifying ledger formats (§2).
3. Multi-host writer election in scope (requires the consensus service DSM defers, `dsm/store.py:53`), or single-host durable fencing sufficient?
4. Should `PURGED` remain a state overwrite or become a separate retention flag?
5. Direct verifier imports from MS-01/MS-02 and the kernel → MS-02 lazy edge in `residual/core.py` (§3.2–3.4): acceptable as-is, or route through a narrow interface?

## 5. Adoption checklist (maintainer steps, out of scope for this PR)

- [ ] Owner decision on §4.1 (violation) and §4.5 (verifier imports)
- [ ] `pip install import-linter` as dev dependency; `lint-imports --config .importlinter` green (or documented exemptions)
- [ ] CI job running `python3 scripts/check_seam_layers.py` (or `lint-imports`) as a required status check — requires `workflow` scope; deliberately not included in this PR
