# SPEC-EVPR-001 — Evidence-Preserving Reducer for Delegated Reading

**Status:** Draft for v2 backlog
**Lane:** Verification / trust boundary
**Depends on:** CAS artifact store (exists), blob-hash verification (exists), run ledger (exists)
**Conflicts with:** None known; additive

---

## 1. Problem

Delegated reading — an agent (swarm reviewer, arena provider, subagent) reads a long artifact (CI log, file tree, test output) and returns a summary to the orchestrator — currently trusts fluent prose. A summary can be wrong, hallucinated, or silently truncated, and the orchestrator has no cheap way to know. This is the trust-boundary gap that #96/#310 work circled: the *content* crossing the boundary is unverified even when the *provenance* (who read what, at which head) is attested.

SoL-Pi's Evidence-Preserving Reducer <REF>cite:tools://web_search:2#3</REF> solves the analogous problem for log summarization: a cheap model produces a compact receipt, and every quoted line is checked verbatim against the archived log before the receipt is forwarded. We port the same discipline to inter-agent evidence.

## 2. Design

### 2.1 Receipt format

Any agent that delegates reading returns an **Evidence Receipt** — a structured object, not prose:

```json
{
  "receipt_id": "rcpt-<ulid>",
  "reader_agent": "swarm-reviewer-3",
  "artifact_ref": "cas://<sha256-of-artifact>",
  "artifact_kind": "ci_log | file_tree | test_output | diff",
  "quotes": [{"line_start":1284,"line_end":1287,"text":"exact verbatim bytes from the artifact"}],
  "findings": [{"claim":"test_foo fails with AssertionError on line 1285","supported_by":["q0"]}],
  "coverage_note": "lines 1-1283 scanned, no anomalies; lines 1288-4001 not scanned (delegated scope)"
}
```

Rules:
- Every `finding` must cite at least one `quote` by index.
- Every `quote.text` must be byte-exact against the artifact.
- `coverage_note` is mandatory — a receipt that does not state what was *not* read is incomplete.

### 2.2 Verification pass

A **Receipt Verifier** module (cheap, deterministic, no LLM) runs before the receipt is admitted to the orchestrator's context:

1. Resolve `artifact_ref` from CAS; fail closed if missing.
2. For each quote: extract artifact lines `[line_start, line_end]`; byte-compare against `quote.text`.
3. Mismatch or missing line range → receipt **rejected**; original artifact (or a larger excerpt) is forwarded instead, and the rejection is recorded in the run ledger.
4. All quotes verified → receipt is stamped `verified` and admitted.

Cost note: verification is O(total quoted bytes), typically three orders of magnitude smaller than the artifact.

### 2.3 Ledger integration

```
EVPR_RECEIPT_VERIFIED  receipt_id  artifact_ref  quote_count  verifier_run_id
EVPR_RECEIPT_REJECTED  receipt_id  artifact_ref  reason  fallback_action
```

### 2.4 Failure modes handled

| Failure | Handling |
|---|---|
| Hallucinated quote | Byte-compare rejects; fallback to direct read |
| Truncated coverage presented as full | `coverage_note` mandatory; orchestrator can require full-coverage receipts for release-gate evidence |
| Receipt cites wrong artifact | `artifact_ref` is CAS hash, not path — wrong artifact means hash mismatch, caught at resolution |
| Verifier itself compromised | Verifier is deterministic code; its run is itself ledgered with exact-head attestation |

## 3. Integration points (existing code)

- **CAS store / blob-hash verification** — reuse as-is; `artifact_ref` is the existing content hash.
- **Run ledger** — new event types `EVPR_*`; no schema migration needed (event-sourced).
- **Agent harness tool surface** — add `emit_receipt` tool for reader agents; add `verify_receipt` internal call in the orchestrator's admission path.
- **Qualification gate** — new qualification scenario: reader agent emits receipt with one planted hallucinated quote; verifier must reject; ledger records rejection. Mutation-verified per your retained-first-attempt-failure rule.

## 4. Non-goals

- Does not verify the *correctness of interpretation* — only that quoted evidence is real. Interpretation quality remains the reviewer agent's job.
- Does not replace human review for release gates; it makes machine-evidence admissible *before* human review.

## 5. Acceptance criteria

1. A reader agent can emit a receipt; verifier admits it when quotes are exact.
2. A receipt with one altered byte in one quote is rejected, fallback fires, ledger records rejection.
3. A receipt with no `coverage_note` is rejected at schema validation.
4. Qualification scenario (planted hallucination) passes mutation verification.
5. Zero changes to existing artifact storage or attestation flows.
