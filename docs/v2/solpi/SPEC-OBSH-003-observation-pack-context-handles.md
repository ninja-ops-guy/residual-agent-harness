# SPEC-OBSH-003 — ObservationPack Context Handles over CAS

**Status:** Draft for v2 backlog
**Lane:** Context economics
**Depends on:** CAS artifact store, run ledger
**Conflicts with:** None; pure addition to agent context layer

---

## 1. Problem

When agents replay long CI logs, file trees, or test outputs into prompts, they pay cache + token costs for content that is already content-addressed in the CAS store. SoL-Pi's ObservationPack archives large tool outputs locally and leaves a stable handle + short excerpt in context, with exact paged recall on demand <REF>cite:tools://web_search:2#0</REF>. Residual v2 needs the same discipline: the ledger already stores the bytes; the context layer should reference them by handle.

## 2. Design

### 2.1 Handle format

```
obs://<sha256>#L12-48
obs://<sha256>#B4096-8192
obs://<sha256>
```

Handles are only valid if the artifact exists in CAS. A handle with an invalid hash fails closed at resolution time.

### 2.2 Tool surface changes

- `read_artifact`: returns handle + first N lines excerpt instead of full content when content exceeds threshold (default 200 lines / 16KB).
- `recall obs://...`: fetches exact paged content from CAS into context on demand.
- `grep_artifact cas://<sha256> pattern`: server-side search returning matching line ranges as handles.

### 2.3 Cache economics

- Artifacts over threshold are **never** auto-included in context.
- Handles are stable strings.
- `recall` is explicit.

### 2.4 Ledger integration

```
OBS_ARCHIVE  artifact_ref  size_bytes  excerpt_handle
OBS_RECALL   artifact_ref  range       requesting_agent  turn
```

Token accounting per run separates "handle tokens" from "recall tokens".

## 3. Integration points

- **CAS store** — unchanged.
- **Agent harness** — threshold behavior plus recall tooling.
- **Run ledger** — new `OBS_*` event types.
- **Token metering** — usage records gain `kind: handle|recall|native`.

## 4. Non-goals

- Does not change what agents are allowed to see.
- Does not deduplicate across runs.

## 5. Acceptance criteria

1. `read_artifact` on a 10,000-line log returns handle + excerpt under the token threshold.
2. `recall` on a valid handle returns exact bytes; invalid hash fails closed with a ledger event.
3. Two consecutive turns referencing the same handle show cache-hit behavior in usage records.
4. Token metering distinguishes handle vs recall tokens.
5. Qualification scenario completes a review task on a large log using handles, with lower token cost than baseline, at equal task score.
