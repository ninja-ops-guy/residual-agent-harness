# OpenClaw Integration

Residual can use OpenClaw as a governed execution substrate through `OpenClawEngine`.

> **OpenClaw executes; Residual decides whether the execution counts.**

This integration deliberately does not turn OpenClaw into Residual's scheduler, verifier, policy authority, receipt authority, or evidence authority. It is an `ExecutionEngine` beneath the same deterministic routing and verification boundary used by other runtimes.

## Architecture

```text
TaskSpec + ContextAssembly
          |
          v
   CapabilityRouter
          |
          v
    OpenClawEngine
          |
          v
 OpenClaw Gateway /v1/responses
          |
          v
 OpenClaw runtime / tools / model
          |
          v
 normalized EngineResult
          |
          v
 Residual evidence + verification + receipts
```

Residual remains authoritative for WorkerContracts, brakes, HITL, evidence validation, verification, integration decisions, and Station receipts. OpenClaw policy, sandboxing, provider safety features, and runtime controls are defense-in-depth controls and are not accepted as independent proof that a Residual contract was satisfied.

## Files

- `residual/engines/openclaw_adapter.py` — gateway adapter and configuration.
- `residual/engines/__init__.py` — public exports.
- `tests/test_openclaw_adapter.py` — deterministic adapter contract tests.
- `docs/specs/SPEC-OPENCLAW-001.md` — normative requirements and acceptance criteria.

## Configuration

```python
from residual.engines import OpenClawConfig, OpenClawEngine

config = OpenClawConfig(
    gateway_url="http://127.0.0.1:18789",
    model="openclaw",
    capabilities=("agent", "code"),
)
engine = OpenClawEngine(config)
```

Authentication can be supplied explicitly through configuration or through `OPENCLAW_GATEWAY_TOKEN`. Credentials are request-only data and are not copied into `EngineResult` metadata or traces.

The adapter uses the Gateway's OpenAI-compatible `/v1/responses` surface. A transport can be injected for deterministic tests or controlled deployments, so the package does not require an OpenClaw Python dependency.

## Routing

`OpenClawEngine` implements the normal `ExecutionEngine` protocol. Register it with `CapabilityRouter` like any other engine; no OpenClaw-specific router branch is required.

```python
from residual.engines import CapabilityRouter

router = CapabilityRouter()
router.register(engine, ("agent", "code"))
selected = router.select("code")
```

The existing deterministic/locality routing rules remain authoritative.

## Task mapping

Residual sends the task input plus context through the OpenClaw request. Runtime selection may be requested through task metadata when a deployment supports it. Configuration is a request, not evidence: if the response does not expose the runtime identity that actually executed the work, Residual records runtime provenance as unverified rather than inferring it.

Example bounded task:

```python
from residual.engines import ContextAssembly, TaskSpec

result = engine.execute(
    TaskSpec(
        task_id="worker-17",
        capability="code",
        input="Implement the bounded change.",
        metadata={
            "allowed_tools": ["read", "write"],
            "openclaw_runtime_id": "codex",
        },
    ),
    ContextAssembly({"repository": "worktree-17"}),
)
```

## Tool enforcement

OpenClaw may have its own allow/deny policies. Residual does not treat their existence as proof of compliance.

When `allowed_tools` is present, the adapter inspects observable tool calls returned by the execution. An observed tool outside the Residual allowlist raises `ContractError` and the execution is not accepted as a valid engine result.

This is intentionally fail-closed for observable violations. Absence of observable tool-call evidence is not converted into a claim that no other action occurred; higher-level Residual verification remains responsible for deciding whether available evidence is sufficient.

## Normalization and provenance

The adapter normalizes OpenClaw Responses-style output into `EngineResult`, including candidate output, observable tool calls, token usage when available, wall-clock duration, and sanitized runtime metadata.

Runtime identity is recorded only when it is observable in the response. Missing runtime identity remains unknown/unverified. Gateway metadata records only a sanitized origin; bearer credentials and URL credential/query material must not enter receipts, traces, or result metadata.

OpenClaw execution provenance can then be bound to the normal `EngineExecutionReceipt`/Station receipt flow without changing the persisted StationReceipt v1 contract.

## Health and failure semantics

`health()` performs no hidden network I/O. Invalid/unusable configuration is reported through the engine health contract. Network failures, malformed responses, timeouts, and observed contract violations fail as adapter/execution errors rather than being converted into successful candidates.

The adapter does not silently fall back to another provider. Service continuity belongs to Residual's explicit routing/fallback layer so the selected execution path remains deterministic and auditable.

## Security boundary

The integration intentionally does **not**:

- grant OpenClaw authority to approve a result;
- trust an OpenClaw policy declaration as evidence of compliance;
- expose gateway credentials in result metadata;
- infer sandboxing or runtime identity that was not observed;
- perform hidden health-check network calls;
- silently reroute failed work;
- bypass Residual WorkerContracts, brakes, HITL, CIC/verification, evidence, or receipts.

## Testing

Run the dedicated adapter tests:

```bash
python -m unittest tests.test_openclaw_adapter -v
```

Run the full repository contract suite before merge:

```bash
python -m unittest discover -s tests -v
```

The adapter tests use injected transports and therefore require neither a live OpenClaw installation nor credentials. Repository CI additionally runs the full suite on Python 3.11, 3.12, and 3.13.

## Normative specification

`docs/specs/SPEC-OPENCLAW-001.md` is authoritative when this guide and implementation commentary differ. The integration's central invariant is that heterogeneous runtime capability can expand beneath Residual without expanding the runtime's authority over verification.