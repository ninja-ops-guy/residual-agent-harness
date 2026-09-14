# v0.4.0 Repo Assessment — Honest Gap Analysis

**Date:** 2026-09-13
**Repo:** https://github.com/ninja-ops-guy/residual-agent-harness
**Analyst:** Independent review against specs

---

## Executive Summary

The repo is substantially more sophisticated than the track
implementations I provided. The receipt system, extension registry,
and HITL gateway are production-grade with design decisions I did
not anticipate. The station layer (service.py at 29K, models.py at
19K, server.py at 20K) is a full web application with real Git
worktree isolation.

However, there are specific gaps between the repo state and the
Phase 4-5 specs that represent the next build targets.

---

## What Exceeds My Track Implementations

### receipts.py — Genuinely Novel Design

| Feature | My Track 1 | Repo v0.4.0 | Assessment |
|---|---|---|---|
| Receipt hash | Computed in __post_init__ | Schema-versioned domain hash with envelope | Repo is better |
| Serialization | asdict() | Canonical with strict_json round-trip validation | Repo is better |
| Parent references | Full StationReceipt objects | Typed ReceiptReference (task_id + hash only) | Repo is better — prevents memory bloat |
| Cycle detection | None | Duplicate/self-dependency rejection in __post_init__ | Repo is better |
| Wire format | None | Versioned envelope with from_dict/from_json | Repo is better |
| Cache key | Static method on class | Standalone function with full validation | Repo is better — cleaner separation |
| Receipt graph validation | None | Full DAG validation with topological resolution | Repo has it, I don't |
| Verdict typing | str | CheckResult enum with SKIPPED rejection | Repo is better |

**Key insight I missed:** The repo separates `ReceiptReference`
(task_id + receipt_hash) from `StationReceipt` (full data). This
is the correct design — parent receipts in a DAG only need to
bind hashes, not carry full receipt data. My implementation
embedded full parent objects, which would cause exponential
memory growth in deep DAGs.

### extensions.py — More Defensive Than Mine

| Feature | My Track 1 | Repo v0.4.0 | Assessment |
|---|---|---|---|
| Freeze point | Constructor flag | Constructor flag + active run lock | Repo is better |
| Boolean policy detection | Runtime probe call | Signature annotation inspection | Repo is better — no side effects |
| Verifier revision | Not implemented | VerifierRevision with implementation/config/policy hashes | Repo has it, I don't |
| Brake lifecycle | Basic protocol check | Per-run instance creation with weakref recycling prevention | Repo is better |
| Brake error handling | None | _GuardedBrake wraps all exceptions into ABORT trips | Repo is better |
| Module lifecycle | Basic hooks | Diagnostics collection for hook failures | Repo is better |
| Legacy verifier support | None | Tuple → VerifierDescriptor migration path | Repo has it, I don't |

**Key insight I missed:** The repo's `_GuardedBrake` wrapper is
the correct safety pattern. If a module's brake raises an exception,
the wrapper converts it to an ABORT trip rather than letting the
exception propagate. My implementation had no such protection.

**VerifierRevision is the missing piece I should have built:**
The repo binds not just a version string but three separate hashes:
implementation_hash (the code), configuration_hash (the params),
policy_hash (the rules). This means a config change without a code
change still invalidates the cache. My implementation used a single
opaque version string.

### hitl/gateway.py — Production-Ready

The repo's HITL implementation uses SQLite for durability, supports
replay prevention, and accepts a host-supplied authenticator callback.
My implementation used JSON files and hardcoded signature matching.
The repo's design is correct for production — the authenticator
should be host-supplied, not built into the gateway.

### station/ — Full Web Application

The station layer has:
- Real HTTP server (server.py, 20K)
- Git worktree isolation (workspace.py, 8.8K)
- Task queue with leases (service.py, 29K)
- Web UI (static/app.js, 57K)
- JSON schemas for validation (schemas/)
- Worker process management (worker.py, 5.6K)
- Observability integration (observability.py, 6.6K)

My track implementations had none of this. The station is a
complete product, not a stub.

---

## Gaps Against Phase 4-5 Specs

### Critical (Blocks production claim)

**1. Engine adapters don't exist**
- No `residual/engines/` directory
- No `ExecutionEngine` protocol
- No LangGraph, CrewAI, or SDK adapters
- The `ai_providers/` package has provider-level adapters
  (Ollama, OpenAI, etc.) but not framework-level adapters
- SPEC-ECO-001 through SPEC-ECO-004 are unimplemented

**2. Async I/O not integrated**
- No `residual/async_io/` directory
- The station server is likely threaded but not async
- Telemetry fetch is synchronous (blocks verification)
- SPEC-PROD-002 is unimplemented

**3. Prometheus export missing**
- No `residual/observability/` directory
- station/observability.py exists but is for the station's
  internal event system, not Prometheus format
- SPEC-PROD-003 is unimplemented

### High (Needed for ecosystem)

**4. Module marketplace absent**
- No `pyproject.toml` entry_points for modules
- No module validation suite
- No package signing
- SPEC-ECO-005 is unimplemented

**5. Documentation incomplete**
- docs/ has architecture and research docs
- No quickstart guide
- No module development tutorial
- No reference architectures
- SPEC-ECO-006 is partially implemented

### Medium (Polish)

**6. Trajectory regression not wired**
- residual/trajectory/recorder.py exists (5.4K)
- No automatic hook into LoopController's on_run_closed
- No golden trajectory store management

**7. Epistemic memory not wired**
- residual/memory/store.py exists (5.1K)
- No automatic indexing at run close
- No retrieval path during context assembly

**8. TUI not wired to observation bus**
- residual/tui/dashboard.py exists (6.1K)
- No live integration with running station

---

## What The Repo Has That No Spec Covered

**modular.py** — A modular execution system I didn't spec
**study.py / study_tasks.py** — Research study framework (29K + 10K)
**evaluation.py** — Evaluation harness
**demo.py** — Demo mode
**cli.py** — Command-line interface
**config.py** — Configuration management
**vendor/ldd-kit** — Vendored dependency with provenance tracking

These suggest the repo has evolved beyond the specs in directions
I didn't anticipate. The study framework in particular suggests
this is being positioned as a research platform, not just an
operations tool.

---

## Recommended Next Steps (Revised)

Given the actual repo state, the priority order changes:

**P0: Engine adapters** — The "control plane" vision needs these.
Build `residual/engines/` with the ExecutionEngine protocol,
then LangGraph adapter as proof of concept.

**P1: Async I/O** — The station server needs this for production
scale. Telemetry and HITL HTTP should not block verification.

**P2: Prometheus export** — Operators need metrics. The
observation layer already has the events; export them.

**P3: Wire trajectory/memory/TUI** — These exist as modules but
aren't connected to the run lifecycle. Connect them.

**P4: Module marketplace** — Once engine adapters prove the
ecosystem model, build the distribution mechanism.

**P5: Documentation** — Quickstart, tutorial, reference
architectures. The repo has excellent internal docs but no
onboarding path.
