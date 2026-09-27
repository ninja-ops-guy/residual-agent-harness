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


---

## AX21-OBS-P3.3-GATEWAY-PROVENANCE-20260925-005

### Scope

Host: DELL7320  
Seat: Wrench  
OpenClaw: 2026.5.28 (e932160)  
Gateway: systemd MainPID 25567

Evidence class:
- P3.3 gateway-binding addendum;
- per-turn result JSON;
- systemd gateway journal correlation;
- configuration-generation evidence;
- preserved embedded-path first observation plus gateway-mediated repeat.

### Historical correction preserved

The original P3.3 A→B→C turns requested gateway execution but were denied the required CLI device scope and silently executed through the embedded path.

The original result is retained as:

`PASS_WITH_TRANSPORT_LIMITATION`

with:
- selection authority: PASS;
- hot reload: PASS;
- A→B→C reversibility: PASS;
- semantic restore: PASS;
- production-session stickiness: PASS;
- failover classification: PASS;
- gateway transport binding at original-run time: NOT_PROVEN.

The limitation is not rewritten away.

### F-2 resolution

The CLI device scope ladder was resolved through explicit device approval. A later gateway-mediated mini-experiment retained, per turn:
- requested transport;
- actual transport;
- fallback source;
- gateway PID/identity;
- session identity;
- provider/model;
- configuration generation;
- gateway journal marker.

All A/B/C turns in the mini-experiment were attributed to the same gateway MainPID 25567 and carried unique journal markers.

Observed sequence:

```
A: kimi/kimi-for-coding
→ mutate default binding
B: moonshot/kimi-k2.6 selected; existing billing cooldown caused skip/fallback to ollama/qwen2.5-coder:7b
→ restore
C: kimi/kimi-for-coding
```

Final P3.3 disposition from the supplied addendum:
- selection authority: PASS;
- hot reload: PASS;
- A→B→C reversibility / semantic restore: PASS;
- production-session stickiness: PASS;
- gateway transport binding: PASS;
- F-2: RESOLVED.

### Environmental positive control

The Moonshot billing/cooldown condition is retained as environmental evidence, not as a product failure. It demonstrated that a degraded selected provider could be skipped and the configured fallback chain engaged.

### Research implication

Execution-path provenance is a separate experimental axis from provider/model selection.

A correct provider result is insufficient evidence of the intended transport. Future AX-21 receipts should retain requested transport, observed transport, fallback source, gateway process identity, session identity, provider/model, and configuration generation independently.

---

## AX21-OBS-SC-FALLBACK-CONTINUITY-20260925-006

### Scope

Experiment: SC-FALLBACK-001-WRENCH  
Host: DELL7320  
Seat: Wrench  
Gateway: systemd MainPID 25567  
Window: 2026-09-25 22:36–22:58 ET

Evidence class:
- immutable qualification receipt;
- per-turn JSON;
- gateway journal extract;
- persistent checkpoint;
- original provider endpoint record.

### Provider-loss experiment

The Kimi provider endpoint was temporarily changed to dead loopback `127.0.0.1:1`, producing a bounded connection-refused/fetch failure while the gateway process remained alive.

The gateway then recorded the configured fallback decision:

```
kimi/kimi-for-coding
→ ollama/qwen2.5-coder:7b
```

The Kimi endpoint was subsequently byte-restored and a fresh session again selected Kimi.

### Continuity observation

A three-stage deterministic workload remained on one session:

```
Stage 1 — Kimi:
41 × 2 = 82
checkpoint persisted

provider loss

Stage 2 — Ollama qwen2.5-coder:7b:
82 + 7 = 89
Stage 1 not repeated

Stage 3 — Ollama qwen2.5-coder:7b:
89 × 3 = 267
Stage 2 not restarted
```

The reconciliation turn reported each stage exactly once. The receipt reports one assistant payload per qualification turn and no stale Ollama binding after restoration.

### Paired claim

This observation and AX21-OBS-P3.3-GATEWAY-PROVENANCE-20260925-005 establish different properties:

```
P3.3
→ configuration / selection authority
→ hot reload and semantic restore
→ requested-vs-observed gateway transport provenance

SC-FALLBACK-001
→ actual primary transport failure
→ configured local fallback selection
→ continued task/session reasoning across provider loss
→ restoration and replay/duplicate checks
```

Neither observation substitutes for the other.

### Preserved limitation — W-1

The local qwen2.5-coder:7b fallback preserved reasoning and session continuity, but tool execution was not equivalent to the primary provider.

The receipt reports that tool calls appeared as raw JSON text and a stage-2 write did not persist, despite the arithmetic/state continuation being correct.

Therefore the supported claim is:

```
local fallback keeps the tested seat alive and reasoning-continuous
```

and NOT:

```
local fallback is a transparent full-capability replacement for the primary
```

Fleet rollout must preserve this distinction through an explicit degraded/tool-free policy or equivalent capability-aware admission.

### Additional retained observations

- W-2: connection-refused surfaced as `fetch failed` and was classified as failover-worthy timeout.
- W-3: primary-recovery clearing appeared turn-driven rather than an observed idle background probe.
- W-4: CLI↔gateway scope negotiation must be pre-approved for automation; embedded execution must be detected rather than silently accepted.

### Research implication

Provider resilience should be modeled as a typed capability transition rather than a binary UP/DOWN state.

A fallback can preserve:
- session continuity;
- reasoning continuity;
- provider availability;

while simultaneously degrading:
- tool execution;
- persistence side effects;
- other capability classes.

Candidate v2 direction:

> Bind fallback admission and continuity receipts to an explicit capability vector, so recovery can distinguish ALIVE_AND_EQUIVALENT from ALIVE_BUT_DEGRADED without treating successful text generation as proof of full execution equivalence.

This is an AX-21 research observation, not a frozen v1 product requirement.

---

## Paired-evidence disposition

The two receipts are retained as complementary AX-21 evidence:

| Evidence | Property established | Important limitation |
|---|---|---|
| P3.3 gateway-binding addendum | configuration/selection authority and gateway execution-path provenance | original A/B/C was embedded; historical limitation remains preserved |
| SC-FALLBACK-001-WRENCH | actual Kimi-loss → Ollama fallback and session/task reasoning continuity | qwen2.5-coder:7b tool execution is degraded/not equivalent |

Current research classification:
- gateway transport provenance: **PROVEN on the mini-experiment**;
- Kimi → Ollama provider resilience: **PROVEN on Wrench**;
- reasoning/session continuity across provider loss: **PROVEN on Wrench**;
- full tool-capability equivalence of qwen2.5-coder:7b: **NOT_PROVEN / observed degraded behavior**;
- fleet-wide equivalence: **NOT_PROVEN**.

### Convergence firewall

These observations remain in the Shared Comms / AX-21 research lane.

They do not enter a v1 convergence candidate unless a separate handoff demonstrates violation of an existing v1 invariant with exact affected SHA, reproduction, severity, minimal repair, regression test, and evidence.
