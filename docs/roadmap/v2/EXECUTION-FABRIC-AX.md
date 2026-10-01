# V2-EF-AX-001 — Execution Fabric / Google AX Adapter

**Disposition:** V2_REVIEW_PENDING / EXPERIMENTAL / disabled by default.  
**Tracker:** [#505](https://github.com/ninja-ops-guy/residual-agent-harness/issues/505).  
**v1 impact:** none intended. This specification must not become a v1 release gate unless new evidence demonstrates violation of an existing v1 invariant.

## 1. Purpose

RESIDUAL needs a vendor-neutral execution boundary so a logical worker/assignment can
run on local processes, containers, OpenClaw, Google AX / Agent Substrate, or future
runtimes without allowing any execution provider to become epistemic or acceptance
authority.

Google AX is the first v2 research target for this boundary because its current
`ax.io/v1alpha1` API exposes small declarative primitives for isolated agent work:
`Task`, `Workspace`, and `Model`; task lifecycle operations; resource limits;
debug/guest access; and suspend/resume backed by a durable `/workspace` volume.

The product boundary is:

```text
RESIDUAL Station / policy / verifier / Evidence Bus
                 |
                 v
        Execution Provider SPI
                 |
        +--------+---------+----------------+
        |                  |                |
      Local             OpenClaw           AX
                                            |
                                      Agent Substrate
                                            |
                                      sandboxed actor
```

**AX executes. RESIDUAL decides whether execution evidence is sufficient to advance
accepted state.**

## 2. Non-goals

This proposal does not:

- make AX, Agent Substrate, Kubernetes, Redis, or a cloud provider a RESIDUAL core dependency;
- treat AX `Ready`, `Running`, `Suspended`, `Failed`, command exit, or any
  provider status as a RESIDUAL PASS;
- grant AX the ability to mint WorkerReceipt/StationReceipt acceptance authority;
- change protected v1 Factory/M3/M4, release, verifier, scheduler, or Station semantics;
- promise AX API stability while AX remains pre-stable/`v1alpha1`;
- execute a live AX cluster experiment from the importable research bench;
- assume that suspend/resume preserves process identity. AX documents durable workspace
  restoration into a fresh container/process tree.

## 3. Normative authority invariants

### EF-AX-I01 — runtime state is observation, not authority

AX lifecycle state is evidence about the execution substrate only. It MUST NOT directly
produce RESIDUAL accepted state.

```text
AX Ready/Running/Completed-like observation
        -> runtime observation
        -> artifact/evidence capture
        -> independent verification
        -> Station disposition
```

### EF-AX-I02 — exact execution identity binding

Every dispatch MUST bind the RESIDUAL logical assignment/generation to the observed AX
task identity, atespace, relevant workspace identity, provider-adapter revision, and
captured substrate identity when available.

A resume/replacement MAY produce a new runtime/process identity. Continuity MUST be
explicitly rebound; identity inheritance by name alone is forbidden.

### EF-AX-I03 — stale generations cannot advance

Results from an earlier execution generation remain retainable evidence but MUST NOT
advance current accepted state after a successor generation has been bound.

### EF-AX-I04 — checkpoint continuity is evidence-bound

Suspend/resume is not proof of semantic continuity. At minimum retain pre/post:
assignment generation, checkpoint/suspend event identity, workspace/artifact digests,
runtime identity, and verification outcome.

### EF-AX-I05 — workspace provenance is not implied by readiness

`WorkspaceReady=True` means the AX workspace-preparation condition succeeded. It does
not prove the repository revision, file set, dependency graph, or experiment baseline
matches the RESIDUAL preregistration. Those identities require independent capture.

### EF-AX-I06 — provider failure cannot be rewritten as model failure

Substrate/cluster/provisioning/network/runner failures MUST be classified separately
from agent/model/verifier failures so execution reliability and reasoning reliability
remain measurable.

### EF-AX-I07 — negative and unknown evidence is retained

FAIL, UNKNOWN, BLOCKED, rejected, missing, contradictory, stale and crash observations
belong in the research/evidence package. A later successful rerun does not erase them.

## 4. Execution Provider SPI

The v2 Execution Provider SPI SHOULD expose the following conceptual operations. Method
names are descriptive until an implementation PR freezes the Python/protocol surface.

```text
discover()             -> provider identity/capabilities
qualify()              -> bounded qualification result; never Station authority
provision(spec)        -> execution handle
bind_identity(handle)  -> exact runtime/logical identity observation
dispatch(handle, work) -> provider-native start/continue request
observe(handle)        -> append-only runtime observations
checkpoint(handle)     -> provider checkpoint/suspend observation
suspend(handle)        -> lifecycle request + evidence
resume(handle)         -> successor runtime observation + rebinding requirement
terminate(handle)      -> bounded teardown request
collect_evidence()     -> immutable provider observations/artifact references
attest()               -> provider-side attestation, if any; evidence only
```

All providers MUST return evidence-oriented results. No SPI implementation may call a
Station acceptance path merely because a provider operation succeeded.

## 5. Core data contract

A future implementation SHOULD normalize execution observations into a record containing
at least:

```json
{
  "schema": "residual.execution-observation.v1",
  "provider": "google-ax",
  "provider_api": "ax.io/v1alpha1",
  "provider_adapter_revision": "<content/revision identity>",
  "logical_assignment_id": "<residual assignment>",
  "logical_generation": 7,
  "provider_execution_id": "<task identity>",
  "provider_scope": "<atespace>",
  "workspace_refs": [],
  "runtime_identity": {},
  "event": "READY|SUSPEND|RESUME|EXIT|FAULT|ARTIFACT|...",
  "provider_state": {},
  "artifacts": [],
  "capture_time": "<observed time>",
  "authority": false
}
```

The schema separates provider statements, local observations, derived facts, verifier
results and Station authority. A provider observation is never silently upgraded into a
verification result.

## 6. Google AX mapping

| RESIDUAL concept | AX surface | Boundary |
| --- | --- | --- |
| bounded execution | `Task` | task state is runtime evidence |
| prepared working set | `Workspace` | readiness does not prove source identity |
| model configuration | `Model` | provider/model config does not imply model qualification |
| isolate/provision | Agent Substrate actor | substrate identity is captured when available |
| observe | task phase/conditions, runner metadata, logs | observation only |
| checkpoint | `ax suspend` | capture pre-suspend evidence |
| resume | `ax resume` | new runtime identity requires rebinding |
| operator debug | `ax ssh` when `debug: true` | privileged research/operator surface |
| custom integration | runner contract | future RESIDUAL-native runner candidate |

The current AX runner contract is especially useful because the runner is PID 1, receives
`AX_TASK_YAML` and `AX_WORKSPACES_YAML`, prepares workspaces, exposes health/readiness
metadata, supervises the command, and remains alive after the command exits. That final
property is a deliberate contradiction test: **runner/task readiness cannot be treated as
proof that the agent command produced an acceptable result.**

## 7. Security boundary

1. The adapter is disabled until explicitly configured.
2. No ambient credential discovery is part of the initial research bench.
3. Model/API secret material MUST remain referenced through provider-native secret
   mechanisms and MUST NOT enter RESIDUAL receipts, preregistration JSON, issues or logs.
4. Debug/SSH is opt-in because it permits arbitrary process/file access inside the task.
5. Repository/workspace inputs MUST reject embedded credentials in URLs.
6. Provider task/image/model/workspace identities SHOULD be content/revision pinned where
   the upstream system permits it.
7. Network egress, MCP, skills and model access are capabilities requiring explicit
   experiment/deployment policy; workspace declaration is not permission escalation.
8. Teardown failure, orphaned tasks and partial suspend/resume MUST remain visible states.

## 8. Cost and resource evidence

The SPI SHOULD keep requested limits separate from observed usage. For AX, retain declared
CPU/memory requests/limits plus observed substrate/resource accounting when available.
Missing cost/token/resource data remains UNKNOWN, never zero.

Future RESIDUAL-PERF work SHOULD measure:

- provisioning latency;
- workspace preparation latency;
- execution latency;
- suspend/checkpoint and resume latency;
- verification tax;
- rework/retry count;
- CPU/memory/network usage where observable;
- model/token/billing usage where authoritative provider data exists;
- evidence volume/storage overhead.

## 9. AX-21 research campaign

The first campaign SHOULD compare a stable control with explicit fault cells.

### Baseline

```text
preregister
  -> provision AX Workspace + Task
  -> bind exact execution identity
  -> execute bounded assignment
  -> capture artifacts/runtime observations
  -> independent verification
  -> Station disposition
  -> teardown
```

### Continuity cell

```text
execute
  -> checkpoint evidence
  -> suspend
  -> resume
  -> observe changed runtime identity
  -> rebind same logical assignment
  -> continue
  -> verify continuity/artifacts
```

### Required adversarial cells

1. **False completion/readiness:** provider remains Ready/Running while required result
   evidence is absent or the agent command has exited.
2. **Actor crash:** crash after a durable checkpoint boundary.
3. **Stale generation:** deliver a pre-resume/pre-replacement result after successor bind.
4. **Workspace mutation:** mutate source/artifact identity after baseline capture.
5. **Identity rebind:** resume into a fresh runtime/process identity.
6. **Transport partition:** interrupt observation/Shared Comms without fabricating failure.
7. **Checkpoint corruption/missingness:** classify as FAIL/UNKNOWN/BLOCKED according to
   observed evidence, not desired recovery result.
8. **Resource exhaustion:** preserve substrate failure separately from model/task quality.

## 10. Measurements and hypotheses

Primary research question:

> Can RESIDUAL preserve evidence/authority invariants while dynamically provisioning,
> suspending, resuming and replacing sandboxed agent executions through an external
> execution control plane?

Required measurements include false acceptance, false rejection, stale-result rejection,
continuity success, evidence completeness, recovery latency, orchestration tax and
resource cost. A green AX workflow is not by itself a positive experiment outcome.

## 11. Importable research bench

`residual.workbench.ax_research` is the initial planning apparatus. It:

- performs no network, subprocess, filesystem or cluster action at import time;
- validates AX RFC-1123 names and HTTPS repository references;
- defines frozen experiment/workspace/task/fault/invariant records;
- creates deterministic preregistration JSON and SHA-256 identities;
- emits dependency-free AX `Workspace` + `Task` documents;
- includes a recommended continuity/fault matrix;
- carries `authority: false` and interpretation rules in preregistration output.

It intentionally does **not** call `ax apply`, `kubectl`, a model API, Shared Comms,
the Evidence Bus, Station, or a verifier. Execution tooling is a later, separately
reviewed layer.

## 12. Qualification gates

| Gate | Initial state |
| --- | --- |
| spec + importable planning bench | IMPLEMENTED IN REVIEW CANDIDATE |
| offline contract/negative tests | REQUIRED |
| whole-repository CI | REQUIRED |
| AX version/API compatibility qualification | NOT RUN |
| Agent Substrate identity capture | NOT IMPLEMENTED |
| live local/dev cluster canary | NOT RUN |
| false-completion contradiction cell | NOT RUN |
| suspend/resume continuity cell | NOT RUN |
| stale-generation fencing | NOT RUN |
| workspace mutation detection | NOT RUN |
| actor crash/recovery | NOT RUN |
| transport partition | NOT RUN |
| resource/cost accounting | NOT RUN |
| independent review/reproduction | NOT RUN |
| RESIDUAL-native AX runner | DEFERRED |
| production/enterprise support claim | NOT AUTHORIZED |

Promotion requires exact source/API identities, frozen protocol/workloads, retained
negative cells, and independent review appropriate to the claim.

## 13. Implementation sequence

**EF-AX-P0 — research apparatus:** spec, preregistration bench, contract tests.

**EF-AX-P1 — provider-neutral SPI:** freeze observation/provision/lifecycle interfaces and
a mock provider before binding AX-specific behavior.

**EF-AX-P2 — AX adapter:** discovery, capability/version capture, Task/Workspace projection,
lifecycle observation, bounded teardown.

**EF-AX-P3 — continuity evidence:** suspend/resume, generation rebinding, checkpoint and
workspace provenance.

**EF-AX-P4 — fault qualification:** false readiness/completion, crash, stale result,
mutation, partition, resource exhaustion.

**EF-AX-P5 — custom runner experiment:** evaluate a RESIDUAL-aware AX runner that emits
evidence hooks without bypassing independent verification.

**EF-AX-P6 — scale/performance:** dynamic cohorts, scheduling, verification tax, resource
envelopes, and provider comparison.

## 14. Upstream compatibility posture

AX currently documents its API as `ax.io/v1alpha1` and warns that core concepts,
protocols and specifications are under heavy development with breaking changes expected
before a stable release. The adapter MUST therefore negotiate/capture capabilities and
fail closed on unsupported schema changes. RESIDUAL core MUST NOT import AX packages as a
hard dependency.

Primary upstream references inspected 2026-10-01:

- https://github.com/google/ax
- https://github.com/google/ax/blob/main/docs/concepts.md
- https://github.com/google/ax/blob/main/docs/manifests.md
- https://github.com/google/ax/blob/main/docs/runner.md

## 15. Review rule

This feature belongs to v2 because it expands execution architecture, not because v1 is
missing a required invariant. New AX findings may inform v1 only if they demonstrate an
actual violation of an already-defined v1 release criterion.
