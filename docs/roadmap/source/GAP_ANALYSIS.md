# Residual Command Station v0.2.0 — Gap Analysis

**Date:** 2026-09-13
**Analyst:** Harness architecture review
**Scope:** Full codebase (2,901 LOC Python + station subpackage), docs, tests
**Reference specs:** harness_specs/DESIGN.md, harness_specs/SPECS.md (SPEC-001..008)
**Synthesis sources:** "Harness vs Loop Engineering" (Goyal), "Disaggregated LLM Inference / KV Cache Management"

---

## Executive Summary

Residual Command Station is a genuinely well-constructed harness with
several design decisions that exceed common practice: hash-chained event
ledgers, pre-I/O budget reservation, content-addressed caching with
revalidation, and a disclosure lattice that treats privacy as transitive.
It is not yet a loop-engineered system. The gap is not code quality —
it is architectural scope. The system executes harness passes well but
has no goal-specification layer, no brake system, no quarantine store,
and no loop controller. It is a strong HarnessPass looking for its
LoopController.

---

## 1. What Exists and Is Strong

### 1.1 Evidence integrity — exceeds baseline

| Mechanism | Location | Assessment |
|---|---|---|
| Hash-chained event ledger | `storage.py:Ledger`, `store.py:_event` | Every event binds `previous` hash. `verify_ledger()` detects rewrites. Strong. |
| Pre-I/O budget reservation | `engine.py:_work` (lines 249-268) | Calls and bytes reserved before transport. Failed calls retain reservation. This is correct accounting, not optimistic billing. |
| Content-addressed cache with revalidation | `engine.py:_cache_key`, `_accept` | Cache key binds protocol version, task ID, goal, obligation contract, verifier revision, artifact hashes, and dependency receipts. Cached values are untrusted proposals revalidated before every acceptance. |
| Receipt binding | `engine.py:_accept` (lines 150-158) | Receipt binds cache key, value hash, verifier name, and verifier revision. Parent receipts propagate input changes through dependent cache keys. |
| Disclosure lattice | `core.py:cloud_allowed` (lines 136-139) | An obligation may cross a remote boundary only if the obligation, all its artifacts, and every transitive dependency permit it. Privacy is transitive by construction. |
| Structured error codes | `providers.py:ProviderError` | Safe error codes only; server bodies and secrets never interpolated into error strings. |

### 1.2 Verification model — sound ordering

The `Verdict` three-state model (`pass`/`fail`/`unknown`) with the rule
that `unknown`, malformed results, verifier exceptions, and abstention
never accept (docs/architecture.md lines 29-33) is correct. The host
check is the sole acceptance authority. The model cannot accept its own
output.

### 1.3 Station subpackage — production-grade task orchestration

The station layer (`station/service.py`) implements what the specs call
HarnessPass with real engineering: transactional task queue with
exclusive leases, isolated Git worktrees, committed-before-checked
candidates, revision-bound review, accumulated integration checks before
fast-forward merge, and crash recovery via lease expiry. The
`rebase_disjoint` method (lines 199-218) correctly invalidates candidates
when declared read/write paths change.

### 1.4 Budget model — honest about uncertainty

The `Usage` dataclass (`providers.py:46-61`) distinguishes `reported`,
`estimated`, `unavailable`, and `simulation` token counts. Missing usage
never becomes a zero-dollar bill (`engine.py` lines 105-109: cost is
`None` unless all remote calls have reported usage). This is
fail-visible accounting.

---

## 2. Gap Classification

Gaps are classified by spec reference and severity:

- **BLOCKER:** Missing capability that prevents loop-engineered operation
- **HIGH:** Missing capability that weakens evidence integrity or safety
- **MEDIUM:** Missing capability that limits scalability or flexibility
- **LOW:** Polish, documentation, or future enhancement

---

## 3. BLOCKER Gaps

### G-1: No GoalSpec — goals are strings, not structures

**Spec:** SPEC-001 (all requirements)
**Current state:** The `Task` dataclass (`core.py:106-174`) has a `goal`
field that is a free-text string. The station manifest has a `goal`
field that is also a free-text string. Neither defines success criteria,
budgets, or amendment rules as structured, frozen, verifiable artifacts.

**What exists instead:** The `Obligation` dataclass provides per-node
contracts with host-registered verifiers. This is excellent for
micro-verification but says nothing about macro-termination. The system
knows when an obligation passes; it does not know when the run is done
in any semantic sense beyond "all obligations accepted."

**Gap:** There is no `GoalSpec` with ordered `success_criteria`,
`max_passes`, `token_budget`, `wall_clock_budget_s`, and
`amendment_rule`. The engine's `Limits` dataclass (`engine.py:14-28`)
provides call/byte/token caps but these are operational ceilings, not
goal-directed termination conditions.

**Why it matters:** Without a GoalSpec, the system cannot distinguish
"all obligations mechanically satisfied but the goal is wrong" from
"goal achieved." The loop engineering diagram's core insight — "Goal +
success criteria defined upfront, not a vibe" — has no corresponding
structure.

**Severity:** BLOCKER. This is the foundational gap. Everything else in
the loop layer depends on it.

---

### G-2: No brake system — limits are checked inline, not as state machines

**Spec:** SPEC-003 (all requirements)
**Current state:** Budget checks are inline comparisons in
`engine.py:_work` (lines 249-254) and `station/models.py:model_call`
(line 75: `store.reserve_call`). The station batch loop has a wave cap
(`service.py:278`: `min(300, len(tasks) * 3)`) and per-task attempt caps
(`service.py:283`: `attempt < 3`). None of these are brakes in the spec
sense: independent state machines that subscribe to the observation bus,
maintain structured state, and emit `BrakeTrip` observations on
transition.

**What exists instead:** Hard-coded integer comparisons scattered across
the engine and station service. No `Brake` protocol. No `BrakeTrip`.
No `BrakeDecision`. No observation emission on limit approach or
exhaustion (the engine emits `budget_blocked` as a ledger event but this
is a failure record, not a brake state transition).

**Gap:** The four brakes — MaxIteration, Budget, NoProgress, Completion —
do not exist as independent, observable, resettable components.

**Why it matters:** Inline limit checks cannot distinguish "budget
exhausted because the task is hard" from "budget exhausted because the
agent is stuck in a loop." The NoProgressBrake (same tool call + same
args repeated consecutively) has no implementation anywhere. The
CompletionBrake (all GoalSpec checks pass) cannot exist without G-1.

**Severity:** BLOCKER. Without brakes, the system has ceilings but no
termination intelligence.

---

### G-3: No quarantine store — actions execute immediately upon proposal

**Spec:** SPEC-004 (all requirements)
**Current state:** The engine's `_work` method calls
`provider.generate(packet, ...)` directly (line 271). The station's
`model_call` function calls `provider.generate(packet, cap)` directly
(`models.py:78`). In both cases, the model's proposed actions (updates
and evidence requests) are parsed and either accepted or rejected, but
the *provider call itself* is never held for policy evaluation before
execution.

**What exists instead:** The engine does validate the response protocol
(`_parse`, lines 306-326) and the station validates the files object
(`service.py:154-156`). But these are format checks on the response,
not policy checks on the action before it executes. The evidence request
path (`_request_evidence`, lines 328-356) is the closest thing to a
quarantine — it validates requests against declared evidence, cloud
permissions, and window limits before fulfilling them. But this is
post-hoc: the model has already been called, tokens have already been
spent, and the response has already been received.

**Gap:** There is no `QuarantineStore` that holds proposed actions
before execution, evaluates them against policies, and denies silently
to the agent while observing fully.

**Why it matters:** The disaggregated inference diagram's "Quarantine
Store (Action held — NOT executed)" and "Silent Action Denied is a
Feature" have no corresponding mechanism. Currently, a proposed action
either executes or fails after execution. There is no pre-execution
hold. For tool calls that have side effects (the station's command
checks, future tool integrations), this means irreversible actions
cannot be policy-gated before they run.

**Severity:** BLOCKER. For a system that will eventually execute
model-proposed code changes, file writes, or external API calls, the
absence of pre-execution quarantine is a safety gap.

---

### G-4: No loop controller — runs terminate but are not decided

**Spec:** SPEC-007 (all requirements)
**Current state:** The engine's `run()` method (`engine.py:45-115`)
executes a while loop over the obligation frontier until no ready nodes
remain. It returns a result dict with status `passed`, `partial`, or
`blocked`. The station's `batch()` method (`service.py:274-317`) runs
dependency waves until no ready tasks remain or wave cap is hit.

**What exists instead:** Termination is implicit: the loop exits when
there is no more work. There is no `RunOutcome` enum, no `BrakeDecision`
evaluation, no escalation path, no `AMENDED` state, no structured
distinction between "goal achieved" and "goal abandoned due to resource
exhaustion."

**Gap:** There is no `LoopController` that orchestrates multiple harness
passes, evaluates brake trips, decides continue/escalate/abort, and
produces a structured `RunOutcome`.

**Why it matters:** The engine and station know when they stop. They do
not know why they stopped in any structured, observable, decision-like
sense. "All obligations accepted" and "budget exhausted with 3
obligations unresolved" both produce a return value, but the difference
between these outcomes is encoded in result fields, not in a termination
decision that was evaluated and recorded as such.

**Severity:** BLOCKER. This is the control plane that turns a harness
into a loop-engineered system.

---

## 4. HIGH Gaps

### G-5: No context curator — context is compiled, not curated

**Spec:** SPEC-005 (all requirements)
**Current state:** The engine's `_packet` method (`engine.py:161-215`)
compiles evidence packets using fixed-window seeding, merged intervals,
and an adaptive complete-capsule heuristic. The station's `prepare`
method assembles task context from declared files. Both are
sophisticated packet compilers.

**Gap:** Neither is a curator in the spec sense. There is no
`ContextCurator` that selects what enters the context window based on
relevance to current goal checks, budget compliance, and provenance
rules. The engine's packet compiler is deterministic and rule-based,
which is good, but it does not prioritize by goal relevance because
there is no GoalSpec to be relevant to (G-1).

**Why it matters:** Without a GoalSpec, context assembly cannot be
goal-directed. The system sends what the obligation declares, not what
the goal requires. This is adequate for micro-tasks but will not scale
to complex multi-step goals where relevance judgment matters.

**Severity:** HIGH (blocked by G-1).

---

### G-6: No sub-agent pool — no spawn/terminate/isolation machinery

**Spec:** SPEC-006 (all requirements)
**Current state:** The engine has a two-tier provider model (local +
expert). The station has a worker model with parallel execution. Neither
spawns sub-agents with independent context, isolated tool subsets, or
arm-isolated configurations.

**Gap:** There is no `SubAgentPool`, no `SpawnSpec`, no sub-agent
lifecycle management. The observation layer has `agent.spawned` and
`agent.terminated` event kinds ready, but nothing emits them.

**Why it matters:** The harness engineering diagram's "Sub-agents:
Specialists" box has no corresponding implementation. For complex goals
that decompose into semi-independent sub-tasks, the system currently
relies on the task DAG structure, which is author-defined, not
agent-adaptive.

**Severity:** HIGH. Not needed for v0.3 but required for the full
vision.

---

### G-7: Observation layer not integrated — parallel telemetry systems

**Spec:** Cross-cutting (all specs reference observation integration)
**Current state:** The codebase has two independent telemetry systems:
1. `storage.py:Ledger` — hash-chained run events (engine)
2. `store.py:_event` — hash-chained LDD events (station)

Both are hash-chained. Neither is the `observation_layer` package
(hash-chained `Observation` with `ObservationKind`, filters, sinks,
and query). The observation layer's `ObservationKind` enum includes
`agent.spawned`, `agent.terminated`, `handoff`, `state.transition`,
and `checkpoint` — none of which are emitted by the current codebase.

**Gap:** The observation layer exists as a standalone package but is
not wired into the engine or station. The engine's Ledger and the
station's event chain are structurally similar but use different
schemas, different hash functions (both SHA-256 but different
canonicalization), and different event vocabularies.

**Why it matters:** Three parallel telemetry systems means three
places to check for audit, three formats to normalize for analysis,
and no unified query interface. The observation layer's `query.py`
(replay, latency_summary, error_rate) cannot operate on engine or
station events without a translation layer.

**Severity:** HIGH. Not a correctness gap but an operational one. Every
debugging session will pay this cost.

---

### G-8: Provider layer overlap — two provider abstractions

**Spec:** ai_providers package (Router, Provider protocol)
**Current state:** The codebase has `residual/providers.py` with its own
`Provider` base class, `HTTPProvider`, `CallableProvider`, and
`StationProvider`. The `ai_providers` package has a parallel
`Provider` protocol with adapters for OpenAI, Anthropic, Google, Azure,
Bedrock, and Ollama.

**Gap:** Two provider abstractions with different interfaces:
- `residual.Provider.generate(packet, max_output_tokens) -> Reply`
- `ai_providers.Provider.chat(req: ChatRequest) -> ChatResponse`

The residual interface is packet-oriented (structured JSON in, structured
JSON out). The ai_providers interface is message-oriented (messages in,
response out). Both are valid but they do not interoperate.

**Why it matters:** The station's `model_call` function
(`models.py:61-94`) is tightly coupled to `HTTPProvider`. It cannot
use the ai_providers Router's failover, multi-provider routing, or
observation integration without an adapter. Conversely, the ai_providers
layer cannot be used for residual-style packet compilation without
significant rework.

**Severity:** HIGH. This is the integration debt the user mentioned —
the two zips need a bridge.

---

## 5. MEDIUM Gaps

### G-9: No judge check layer

**Spec:** SPEC-002-R6/R7 (judge checks)
**Current state:** The station has a `review` step (`service.py:220-242`)
that uses an LLM to review candidate implementations against
specifications. This is a judge, but it is hard-coded into the station
pipeline, not available as a composable check type in the engine's
verifier registry.

**Gap:** The engine's `Registry` (`core.py:218-241`) registers checks
and solvers but has no `judge` check type. The station's review is a
pipeline stage, not a registered check.

**Severity:** MEDIUM. The capability exists but is not composable.

---

### G-10: No spec amendment machinery

**Spec:** SPEC-001-R6/R7 (amendment rule)
**Current state:** The station docs state "The original spec is immutable
for a mission" (SPECIFICATION.md line 47). There is no amendment
mechanism.

**Gap:** No `AmendmentRule`, no spec versioning beyond
`schema_version: 1`, no amendment observation emission.

**Severity:** MEDIUM. Immutability is a valid design choice for v0.2 but
will need to evolve for long-running missions.

---

### G-11: No no-progress detection

**Spec:** SPEC-003-R6 (NoProgressBrake)
**Current state:** The engine tracks `self.calls` and `self.failures`
but does not detect repeated identical tool calls. The station tracks
task attempts but does not detect repeated identical model outputs.

**Gap:** No fingerprint-based repetition detection exists anywhere.

**Severity:** MEDIUM. Will waste budget on stuck agents without it.

---

### G-12: Provider coverage limited to Ollama + OpenAI-compatible

**Spec:** ai_providers adapters (Anthropic, Google, Azure, Bedrock)
**Current state:** `HTTPProvider` supports `kind: "ollama"` and
`kind: "openai_compatible"`. The station's `model_call` supports these
two kinds. No Anthropic, Google, Azure, or Bedrock adapters exist in
the residual codebase.

**Gap:** The ai_providers package has these adapters but they are not
integrated (G-8).

**Severity:** MEDIUM (resolved by resolving G-8).

---

## 6. LOW Gaps

### G-13: No streaming support

The engine and station use synchronous request-response. The
ai_providers package supports streaming but it is not integrated.

### G-14: No async execution

The engine is explicitly single-process and synchronous
(docs/architecture.md line 125). The station uses thread pools. Neither
uses asyncio.

### G-15: Bedrock streaming/async stubs

The ai_providers Bedrock adapter has `stream`, `achat`, and `astream`
as stubs that raise `ProviderError(code="not_implemented")`.

---

## 7. Gap Dependency Graph

```
G-1 (GoalSpec)
  ├── blocks → G-2 (Brakes need GoalSpec for budgets/criteria)
  ├── blocks → G-5 (ContextCurator needs GoalSpec for relevance)
  └── blocks → G-4 (LoopController needs GoalSpec for RunOutcome)

G-2 (Brakes)
  └── blocks → G-4 (LoopController evaluates BrakeTrips)

G-3 (QuarantineStore)
  └── independent but highest safety value

G-4 (LoopController)
  └── depends on G-1, G-2

G-7 (Observation integration)
  └── independent, enables all other gaps to emit telemetry

G-8 (Provider bridge)
  └── independent, enables ai_providers adapters in residual
```

**Critical path:** G-1 → G-2 → G-4 (loop layer)
**Parallel track:** G-3 (quarantine), G-7 (observation), G-8 (providers)

---

## 8. Recommended Build Order

| Phase | Gaps | Deliverable |
|---|---|---|
| 1 | G-7, G-8 | Integration layer: observation bus wired into engine + station; provider bridge |
| 2 | G-1 | GoalSpec with frozen criteria, budgets, amendment rule |
| 3 | G-2 | Four brakes as bus-subscribing state machines |
| 4 | G-3 | QuarantineStore with policy evaluation |
| 5 | G-4 | LoopController with RunOutcome enum |
| 6 | G-5, G-6 | ContextCurator, SubAgentPool |
| 7 | G-9..G-15 | Polish, async, streaming, judge composability |

---

## 9. What NOT to Change

The following are correct and should be preserved:

1. **The disclosure lattice** (`cloud_allowed` transitive check) — this
   is the strongest privacy mechanism in the codebase
2. **Pre-I/O budget reservation** — correct accounting that most systems
   get wrong
3. **Cache revalidation** — cached values are untrusted proposals, never
   accepted without re-verification
4. **The `unknown` Verdict state** — abstention and uncertainty never
   accept
5. **Safe error codes** — no server bodies or secrets in error strings
6. **The station's revision-bound review** — approval binds to exact
   commits and check hashes
7. **The three-attempt task cap with cloud escalation** — bounded retry
   with escalation is loop-like behavior already
