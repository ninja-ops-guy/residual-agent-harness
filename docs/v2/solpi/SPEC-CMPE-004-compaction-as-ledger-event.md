# SPEC-CMPE-004 — Compaction as Ledger Event with Economic Gate

**Status:** Draft for v2 backlog
**Lane:** Context economics / auditability
**Depends on:** Run ledger, OBS handles (SPEC-OBSH-003 recommended)
**Conflicts with:** None; behavioral addition to context management

---

## 1. Problem

Context compaction in long agent runs is currently implicit runtime behavior: it happens, but there is no record of *why*, no cost accounting, and no way to answer "what did the agent know at turn N" from the ledger. SoL-Pi's Online Context Compact fires at semantic subtask completion, but only when expected future savings repay the rewrite cost (which breaks KV-cache reuse) <REF>cite:tools://web_search:2#3</REF>. Residual v2 should make compaction an explicit, gated, ledgered decision — auditable context economics.

## 2. Design

### 2.1 Compaction record

```
CMPC_FIRED
  trigger: subtask_complete | token_threshold | explicit
  pre_compaction_context_ref:  cas://<sha256-of-context-snapshot>
  post_compaction_context_ref: cas://<sha256>
  retained_handles: [obs://..., obs://...]
  dropped_content_summary: <structured summary of what was dropped>
  estimated_future_savings_tokens: <int>
  rewrite_cost_tokens: <int>
  kv_cache_invalidated: true
  economic_gate: pass | fail
```

### 2.2 Economic gate

```
estimated_future_savings_tokens > rewrite_cost_tokens * K
```

K defaults to 2.0.

### 2.3 Semantic trigger

Compaction triggers at **subtask boundaries**, not mid-subtask.

### 2.4 Retained handles

Post-compaction context retains:
- current subtask working set;
- handles to anything referenced by open ledger events;
- plan structure.

### 2.5 Auditability

The ledger records context snapshots, the reason compaction fired or did not, and what was dropped.

## 3. Integration points

- **Run ledger** — `CMPC_*` event types; context snapshots are CAS artifacts.
- **Planner/harness** — subtask-boundary hook.
- **OBS handles** — retained handles reference OBS-003 handles.
- **Token metering** — feeds ENVB-002 efficiency accounting.

## 4. Non-goals

- Does not guarantee compaction is optimal.
- Does not prevent context overflow by itself.

## 5. Acceptance criteria

1. Multiple-subtask runs produce `CMPC_FIRED` only at subtask boundaries.
2. Failed economic gates produce `CMPC_SKIPPED`.
3. Context snapshot refs resolve from CAS and byte-match the recorded hash.
4. Reconstructing turn-N context from the ledger is possible and documented.
5. Qualification shows estimated versus measured savings within a recorded tolerance.
