# SPEC-ENVB-002 — Environment Bank for Auto-Research Loops

**Status:** Draft for v2 backlog
**Lane:** M6 autonomous discovery
**Depends on:** D2 experiment infrastructure, WebVM qualification runs, swarm task history
**Conflicts with:** None; prerequisite for M6 loop mechanics

---

## 1. Problem

Residual has raw material in D2 experiments, WebVM qualification runs, and swarm review tasks, but it is not packaged as a bank of replayable environments. Without this, M6's "RESIDUAL discovers improvement" has no fixed substrate for screening ideas against history and validating them against held-out tasks.

## 2. Design

### 2.1 Environment record

```json
{
  "env_id": "env-<ulid>",
  "task_class": "ci_repair | spec_conformance | test_authoring | review_triage | harness_operation",
  "input_artifact": "cas://<sha256>",
  "initial_state": "cas://<sha256-of-workspace-snapshot>",
  "scorer": "scorer://<module-name>",
  "capability_floor": 0.94,
  "token_budget": 150000,
  "provenance": {
    "source": "d2-0004 | webvm-qual-run-17 | swarm-task-88",
    "extracted_at": "<iso8601>",
    "extractor_version": "envb-0.1"
  }
}
```

### 2.2 Scorers

A scorer is a pure function: `(final_workspace, run_ledger) -> {score: float in [0,1], evidence: [...]}`.

Initial scorer set:
- CI repair
- Spec conformance
- Test authoring
- Review triage
- Harness operation

### 2.3 Historical-trace pre-screening

Before a candidate mechanism is run live, replay its decision rule over recorded traces, estimate benefit, and discard candidates below threshold.

### 2.4 Frozen held-out validation

- Environments split `screening` / `validation` at extraction time.
- Candidate passing screening runs on validation once with frozen config.
- Acceptance: score >= capability_floor on every validation environment and token cost strictly lower than baseline.

### 2.5 Token efficiency as selection pressure

The M6 loop optimizes **verification cost per accepted change at fixed capability**, not raw task count.

## 3. Integration points

- **CAS store**
- **Run ledger**
- **D2 infrastructure**
- **WebVM qualification**
- **M6 spec**

## 4. Non-goals

- Not a general external benchmark suite.
- Not a replacement for human review.

## 5. Acceptance criteria

1. At least 50 environments extracted from D2 + WebVM + swarm history, with provenance.
2. Scorer for each of five task classes implemented and unit-tested.
3. Screening/validation split enforced.
4. One candidate mechanism (recommend EVPR-001) screened against historical traces.
5. Extraction reproducible: same source runs → same env_ids.
