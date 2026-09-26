# AX-21 Research Check-in — 2026-09-25

Status: **OBSERVED / NOT FROZEN**

This append-only check-in records live swarm-recovery observations from 2026-09-25. It does not rewrite earlier AX-21 evidence. Prior claims that are no longer accurate are preserved historically and explicitly superseded below.

## AX21-OBS-SUBSCRIBE-MORPH-20260925-003

### Scope

Host: DELL7320

Seats observed:
- Crucible
- Wrench
- Piston

Evidence class:
- live host observation;
- timer-fired subscribe-health monitor receipt;
- corrected monitor artifact with preserved first-failure evidence.

### Observed state transition

Earlier Crucible behavior:
- primary failure signature: `resource_exhausted`;
- approximately 300 s backoff;
- approximately five-minute reconnect cadence;
- `default_chat_id=none`;
- prior interpretation: bridge reachable while room identity/subscription binding was ineffective.

Later Crucible behavior:
- failure signature changed to `stream_closed`;
- backoff changed to approximately 1000 ms;
- reconnect cadence increased to approximately 12 s;
- connections began binding a real `default_chat_id`;
- approximately 119 connects were observed over two hours, consistent with a high-frequency flap cycle.

### Supersession

The earlier statement that Crucible had **zero effective connects** is superseded by this observation.

That prior statement remains part of the historical evidence and MUST NOT be deleted or silently rewritten.

### Interpretation

The underlying fault did not disappear; its observable morphology changed.

A single diagnostic sentinel is therefore insufficient for longitudinal swarm health classification. In particular, the transition from `default_chat_id=none` to a real chat ID did not establish recovery because reconnect pressure and failure churn persisted.

The more durable observable is the transition trajectory:

```
reconnect pressure
+ unresolved continuity/rebind instability
+ sustained failure churn
```

rather than one provider error code or one subscription field.

### Monitor first-failure evidence

The mandated timer-fired observation exposed two defects in the initial monitor artifact.

**FF-1A — journal echo contamination**

Campaign/room messages can be echoed through `msgCtx` journal records. Content-based matching therefore inflated counts when quoted log material re-entered the journal.

Correction:
- require the intended `[plugins] [kimi-bridge]` source anchor;
- exclude `msgCtx` echoes.

**FF-1B — resolved reconnect misclassification**

Healthy Wrench/Piston connections were incorrectly classified from elapsed time since an earlier reconnect event.

Correction:
- evaluate event ordering;
- a reconnect followed by a successful connect is considered resolved rather than remaining critical solely because of elapsed time.

The pre-correction observation is preserved. The corrected artifact was re-digested and two subsequent timer-fired observations classified:
- Crucible: **CRIT**;
- Wrench: **OK**;
- Piston: **OK**.

### Claim boundary

Local DELL7320 silent-storm detection is armed.

Room-level relay / external notification is **not** armed.

Do not claim end-to-end alert delivery from this observation.

### Research implication

Candidate v2 direction:

> Swarm health should be represented as typed, morphology-aware state transitions with explicit supersession of obsolete diagnostics, rather than as independent threshold checks bound to a single error signature.

This is a research direction, not a frozen product requirement.

---

## AX21-OBS-RESOURCE-CONTENTION-20260925-004

### Scope

Host: LEGION

Status: **OPERATING CONSTRAINT / RESEARCH NOTE**

### Observation

Local Codex work and OpenClaw fallback can share the same Ollama/GPU resource domain on LEGION.

### Experimental control

During a measured fallback canary, pause unrelated local `gpt-oss:20b` Codex activity.

Purpose:
- avoid VRAM contention;
- avoid latency contamination;
- avoid provider/model availability interference;
- keep fallback measurements attributable to the canary under test.

### Claim boundary

This is an experiment-isolation control.

It is **not** evidence that local model contention has already caused a fallback failure.

---

## Follow-up

- Preserve the P3.2 pre-fix and corrected monitor digests in the Phase-3 evidence bundle.
- Record future Crucible morphology changes as new append-only observations rather than mutating this record.
- If the room-relay leg is armed later, record that as a separate operational milestone.
- If GPU contention is deliberately tested later, preregister the workload/model combination and resource measurements before execution.
