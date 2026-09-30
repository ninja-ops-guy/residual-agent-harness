# SPEC-ADAPTER-OPENSHELL-R0 — NVIDIA OpenShell Execution Substrate

**Status:** Design candidate / post-v1 roadmap  
**Spec version:** R0  
**Date:** 2026-09-30  
**Repository:** `ninja-ops-guy/residual-agent-harness`  
**Base considered:** `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`  
**Normative language:** RFC 2119  
**Release effect:** **NONE on v1.** This specification MUST NOT become a v1 release criterion unless new evidence demonstrates a violation of an already-existing v1 invariant or release criterion.

---

## 1. Purpose

Define a RESIDUAL execution adapter for NVIDIA OpenShell so an untrusted agent or execution engine can run inside a policy-enforced OpenShell sandbox while RESIDUAL retains authority over:

- task admission;
- mission and worker contracts;
- verification;
- evidence interpretation;
- byte-exact artifact admission when the repository's transport contract requires it;
- deterministic integration;
- human/Station authority gates;
- receipt issuance;
- accepted state.

OpenShell is an **execution and confinement substrate**, not a replacement for RESIDUAL's control plane, evidence model, verifier, scheduler, Factory, Shared Comms, or Station authority.

The integration target is named:

`residual-adapter-openshell`

The initial implementation SHOULD live behind the existing `ExecutionEngine` / engine-adapter seam.

---

## 2. Existing RESIDUAL bindings

This specification extends, and MUST NOT weaken, the following repository contracts:

- `SPEC-CP-001`: framework-neutral engine adapter protocol.
- `SPEC-CP-003`: engine-specific output normalization before verification.
- `SPEC-CP-004`: OS-enforced engine isolation, resource constraints, state protection, network mediation, and crash containment.
- `SPEC-GAP-001`: `ExecutionEngine`, `EngineResult`, deterministic routing, isolated adapters, and engine provenance.
- `SPEC-NINE-001`: engine adapter implementation and end-to-end receipt-backed qualification.
- Factory invariants: workers produce quarantined candidates; Factory execution does not merge or issue Station receipts.

The current `residual/engines/_isolated.py` process boundary remains useful for host-side adapter containment. OpenShell adds a stronger workload isolation/enforcement boundary around the untrusted agent runtime.

### 2.1 Two-layer boundary

The integration MUST distinguish:

1. **Adapter protocol boundary** — host-side RESIDUAL code serializes an approved request and normalizes observable results.
2. **Execution enforcement boundary** — OpenShell gateway/supervisor/compute driver applies sandbox lifecycle, filesystem policy, network policy, process identity, provider/credential handling, and runtime confinement.

Untrusted agent code MUST NOT execute in the RESIDUAL Station process.

---

## 3. Authority model

### OS-R1 — RESIDUAL remains authority

OpenShell MUST be treated as an enforcement substrate and evidence source.

OpenShell MUST NOT independently:

- approve a RESIDUAL mission;
- satisfy a verifier;
- mark a candidate accepted;
- authorize integration;
- merge code;
- mint a RESIDUAL Station receipt;
- elevate an engine capability claim to a verified capability;
- reinterpret a denied RESIDUAL action as permitted.

A successful OpenShell execution proves only what the retained evidence supports about that execution environment and run.

### OS-R2 — OpenShell denial wins at the execution boundary

If RESIDUAL authorizes an action but OpenShell policy denies it, the action MUST remain denied and the run MUST surface a classified execution failure or blocked result.

RESIDUAL MUST NOT automatically weaken OpenShell policy to make a task succeed.

### OS-R3 — RESIDUAL denial wins at the control boundary

If OpenShell would permit an operation but RESIDUAL policy, quarantine, WorkerContract, Station authority, or an applicable human gate denies it, the operation MUST NOT be dispatched merely because the sandbox could perform it.

### OS-R4 — evidence is not authority

OpenShell logs, lifecycle state, policy state, sandbox metadata, provider attachment state, and driver state are evidence. Their presence MUST NOT be interpreted as a RESIDUAL acceptance verdict.

---

## 4. Architecture

```text
RESIDUAL Station / Mission / Factory
        |
        | approved TaskSpec + ContextAssembly
        | authority reference + execution envelope
        v
OpenShellExecutionEngine
(host-side adapter; no untrusted engine code)
        |
        | compile + bind
        v
OpenShell Gateway
        |
        +--> compute driver
        |      Docker / Podman / VM / Kubernetes / future qualified driver
        |
        v
OpenShell Sandbox Supervisor
        |
        +--> effective filesystem policy
        +--> effective network policy
        +--> process identity / privilege boundary
        +--> provider credential placeholders + proxy resolution
        +--> inference route
        +--> lifecycle + security observations
        |
        v
Agent / execution engine
        |
        v
observable result + artifacts + logs
        |
        v
OpenShellExecutionEngine.normalize()
        |
        v
EngineResult + OpenShell evidence bundle
        |
        v
RESIDUAL quarantine -> verifier -> admission -> deterministic integration
        |
        v
Station / human authority gate
```

For Hermes and OpenClaw, NemoClaw MAY be used as an agent-specific lifecycle/profile layer above OpenShell. The base RESIDUAL adapter MUST bind to OpenShell semantics, not to NemoClaw-only semantics.

---

## 5. Execution request contract

### OS-R5 — explicit request object

The adapter MUST compile an immutable `OpenShellExecutionRequest` before creating or selecting a sandbox.

Minimum logical fields:

```text
schema_version
request_id
mission_id
task_id
attempt_id
task_spec_digest
context_digest
authority_ref
engine_name
engine_version
agent_profile
agent_command_argv
image_ref
image_digest              # required for qualified execution
compute_driver_requirement
sandbox_profile
base_policy_digest
provider_refs             # identifiers only; never secret values
inference_route_ref
resource_budget
timeout_s
expected_outputs
output_contract_digest
correlation_ids
created_at
```

The serialized request MUST be canonicalized before hashing.

### OS-R6 — no secrets in request material

The request, TaskSpec, ContextAssembly, logs exported to RESIDUAL, receipts, and evidence bundles MUST NOT contain real provider secret values.

Only provider identifiers, opaque handles, profile identifiers, or redacted metadata MAY cross the adapter boundary.

### OS-R7 — exact executable identity

Qualified execution MUST bind the launched workload to:

- exact image digest;
- exact argv or equivalent canonical main-process specification;
- exact agent/runtime version when observable;
- exact OpenShell version or source identity;
- exact NemoClaw version or source identity when NemoClaw participates;
- exact compute driver class;
- platform identity sufficient to reproduce the qualification class.

Mutable tags alone MUST NOT satisfy a qualified identity claim.

---

## 6. Policy compilation

### OS-R8 — least-privilege compilation

The adapter MUST compile an execution envelope into an OpenShell policy that is no broader than the RESIDUAL-approved task requires.

The envelope MUST distinguish at least:

- readable filesystem roots;
- writable filesystem roots;
- executable/binary scope;
- network destinations;
- provider attachments;
- resource requirements;
- expected output locations;
- lifecycle timeout;
- optional inference route.

Unknown permissions MUST default to denied.

### OS-R9 — static versus dynamic controls

The adapter MUST track whether a requested control can be changed on a live OpenShell sandbox or requires sandbox recreation.

A policy update MUST NOT be reported as effective until OpenShell reports the corresponding effective/revision state and the adapter has retained that state as evidence.

If a required static control cannot be applied to the existing sandbox, the adapter MUST create a new sandbox or fail closed.

### OS-R10 — policy digest binding

The adapter MUST retain:

- requested policy digest;
- effective policy digest when retrievable;
- policy revision identity/status when retrievable;
- any provider-derived policy layer identifiers that materially affect the effective policy.

A mismatch between the requested security envelope and the effective policy MUST produce `UNKNOWN` or `FAIL`, never `PASS`.

---

## 7. Provider and credential handling

### OS-R11 — provider references, not credentials

RESIDUAL SHOULD use OpenShell provider attachments for credentials required by the sandbox.

The adapter MUST NOT retrieve a provider secret merely to forward it into the sandbox.

### OS-R12 — endpoint-bound qualification

A provider credential path is qualified only if tests demonstrate both:

1. the intended binary/destination is permitted; and
2. the same credential cannot be resolved for a disallowed destination/path used by the negative test.

A provider attachment by itself is not evidence that endpoint binding works.

### OS-R13 — secret non-disclosure

Qualification MUST include a bounded test proving the real credential value is not exposed in:

- the agent-visible environment;
- command arguments;
- task/context serialization;
- exported logs;
- EngineResult;
- RESIDUAL evidence bundle.

If the test cannot distinguish placeholder behavior from real-secret exposure, the result is `UNKNOWN`.

---

## 8. Sandbox lifecycle

### OS-R14 — lifecycle states

The adapter MUST normalize OpenShell lifecycle into RESIDUAL-observable states at least equivalent to:

`REQUESTED -> CREATED -> STARTING -> RUNNING -> TERMINAL`

Terminal classifications MUST include:

- `SUCCEEDED`
- `FAILED`
- `TIMED_OUT`
- `POLICY_DENIED`
- `PROVIDER_FAILED`
- `SANDBOX_LOST`
- `ADAPTER_FAILED`
- `UNKNOWN`

Vendor-specific states MAY be retained in raw metadata but MUST NOT replace the normalized classification.

### OS-R15 — timeouts

A RESIDUAL execution timeout MUST terminate or otherwise make the launched task non-authoritative.

If the adapter cannot establish whether the task continued executing after timeout, the execution result MUST be `UNKNOWN` and its outputs MUST remain inadmissible.

### OS-R16 — crash containment

Sandbox, supervisor, agent, gateway-session, or driver failure MUST NOT crash the Station process.

The adapter MUST preserve the first observed failure classification and MUST NOT rerun the task in a way that overwrites first-failure evidence.

---

## 9. Result and artifact contract

### OS-R17 — EngineResult normalization

The adapter MUST normalize observable execution into the existing `EngineResult` contract.

`raw_metadata` SHOULD include a stable reference to an `OpenShellExecutionEvidence` object rather than embedding an unbounded vendor log stream.

### OS-R18 — evidence object

Minimum logical `OpenShellExecutionEvidence` fields:

```text
schema_version
request_digest
residual_source_identity
openshell_identity
nemoclaw_identity           # nullable
sandbox_id
sandbox_generation
compute_driver
platform_class
image_digest
agent_identity
base_policy_digest
effective_policy_digest
policy_revision
provider_attachment_refs
inference_route_ref
started_at
ended_at
normalized_outcome
vendor_outcome
exit_code
stdout_digest
stderr_digest
security_log_digest
lifecycle_log_digest
artifact_manifest_digest
engine_result_digest
first_failure
evidence_completeness
```

Fields not supported by the current OpenShell API MUST be represented as unavailable rather than fabricated.

### OS-R19 — artifact manifest

Every produced artifact that may leave the sandbox MUST appear in a manifest containing at least:

- logical artifact ID;
- path or source locator;
- byte length;
- cryptographic digest;
- media/type hint;
- producing request digest.

The manifest does not itself authorize the artifact.

### OS-R20 — byte-exact transport hook

Where an artifact crosses a transport/admission boundary governed by RESIDUAL's byte-exact transport contract, the receiving side MUST recompute the required digest over the received bytes and obtain the applicable byte-exact verification receipt before admission.

OpenShell sandbox success, file transfer success, or matching metadata MUST NOT substitute for byte-exact admission evidence.

If the governing byte-exact contract is not yet accepted on the target branch, this adapter MUST expose the artifact digest/length inputs needed by that contract and MUST NOT claim that contract is closed.

---

## 10. Observability

### OS-R21 — observation ingestion

OpenShell security/lifecycle observations SHOULD enter the RESIDUAL Evidence Bus through a dedicated adapter.

Vendor events MUST retain their native type and provenance while also receiving a RESIDUAL normalized type.

### OS-R22 — provenance separation

The evidence model MUST distinguish:

- RESIDUAL request facts;
- OpenShell-observed facts;
- NemoClaw-observed facts, if present;
- agent claims;
- verifier results;
- authority decisions.

A vendor observation MUST NOT be rewritten as though RESIDUAL independently observed it.

### OS-R23 — bounded retention

The adapter MUST hash and reference large log streams rather than forcing unbounded logs into receipts or control-plane state.

Retained excerpts MUST be deterministic and bounded.

---

## 11. Compute-driver policy

### OS-R24 — driver qualification is separate

Qualification applies to an exact tuple, not to "OpenShell" generically.

At minimum the tuple MUST bind:

```text
RESIDUAL source
OpenShell version/source
NemoClaw version/source if used
compute driver
host/platform class
sandbox image digest
policy digest
agent/runtime version
provider profile set
```

A PASS on Docker MUST NOT be automatically promoted to Podman, VM/MicroVM, Kubernetes, Windows MXC, or future drivers.

### OS-R25 — initial driver

The first implementation SHOULD target Docker because it provides the smallest post-v1 integration surface for a workstation/CI spike.

Other drivers SHOULD be added only through the same qualification contract.

### OS-R26 — experimental/platform limitations

A platform or driver documented upstream as experimental, partial, or not production-parity MUST retain that limitation in RESIDUAL capability metadata.

RESIDUAL MUST NOT upgrade an upstream support statement through local naming.

---

## 12. NemoClaw profiles

### OS-R27 — optional layer

NemoClaw MAY provide agent-specific onboarding/lifecycle for Hermes and OpenClaw.

The adapter MUST make this explicit with a profile such as:

- `openshell/direct`
- `openshell/nemoclaw-hermes`
- `openshell/nemoclaw-openclaw`

### OS-R28 — lifecycle authority

For NemoClaw-managed profiles, exactly one component MUST own the OpenShell gateway lifecycle.

The selected ownership mode MUST be captured in evidence.

The adapter MUST NOT race an externally managed OpenShell gateway with a second lifecycle manager.

### OS-R29 — agent qualification independence

A qualified `nemoclaw-hermes` profile does not automatically qualify `nemoclaw-openclaw`, and vice versa.

The same applies to model/provider combinations.

---

## 13. Capability routing

### OS-R30 — capability claims

Proposed capabilities include:

```text
sandboxed_execution
filesystem_policy
network_policy
credential_broker
managed_inference
agent_hermes
agent_openclaw
agent_codex
gpu_execution
driver_docker
driver_podman
driver_vm
driver_kubernetes
```

Every capability MUST remain a claim until a probe for the exact qualification tuple passes.

### OS-R31 — no generic "secure" capability

The adapter MUST NOT expose a single boolean named `secure`, `safe`, or equivalent.

Security-relevant capabilities MUST remain decomposed and evidence-backed.

---

## 14. Self-hosting / "RESIDUAL builds RESIDUAL" lane

### OS-R32 — bounded first lane

The first self-build qualification MUST use a disposable repository or isolated fixture and MUST NOT target accepted `main`.

The agent MAY:

1. receive a frozen, bounded change request;
2. modify only approved paths inside the sandbox workspace;
3. run approved tests;
4. emit a patch/artifact manifest.

RESIDUAL MUST then:

5. verify the artifact independently;
6. perform any required byte-exact admission;
7. deterministically integrate only into a disposable or explicitly approved candidate branch;
8. retain all evidence;
9. stop before merge unless an independent Station/human authority gate explicitly authorizes merge.

### OS-R33 — no credentialed write in first spike

The first qualification SHOULD avoid giving the sandbox direct repository write authority.

The preferred first path is artifact/patch return to RESIDUAL, followed by host-side verified integration.

A later qualification MAY test endpoint-bound GitHub write credentials as a separate capability.

---

## 15. Failure semantics

### OS-R34 — fail closed

The following MUST NOT result in `PASS`:

- missing image digest;
- missing required policy evidence;
- policy request/effective mismatch;
- unknown sandbox termination;
- lost gateway session with unresolved execution status;
- provider credential exposure;
- unclassified artifact mutation;
- missing required byte-exact admission evidence;
- unbound agent/runtime identity when the qualification claims exact identity;
- missing first-failure evidence after a retry.

### OS-R35 — retries create attempts

A retry MUST receive a new `attempt_id` and a new request digest.

A successful retry MUST NOT erase the failed attempt.

---

## 16. Non-goals for R0

R0 does not:

- replace FactoryRuntime;
- replace Shared Comms;
- replace the Evidence Bus;
- replace BL-016 or any successor transport/admission contract;
- create a new v1 release gate;
- claim production readiness;
- claim every OpenShell driver is qualified;
- claim GPU execution is qualified;
- grant autonomous merge authority;
- grant autonomous credential escalation;
- require NemoClaw for all OpenShell use.

---

## 17. Implementation shape

Proposed module layout:

```text
residual/
  engines/
    openshell_adapter.py
    openshell_contracts.py
    openshell_policy.py
    openshell_evidence.py
    openshell_client.py
  evidence/
    openshell_observations.py

tests/
  openshell/
    test_contracts.py
    test_policy_compile.py
    test_result_normalization.py
    test_fail_closed.py
    test_evidence_binding.py
    test_provider_redaction.py

scripts/
  qualify_openshell_adapter.py
```

The implementation MAY initially shell out to a pinned OpenShell CLI for the spike, but the production adapter SHOULD prefer a stable machine-readable API/SDK surface when available.

CLI text parsing MUST NOT become the durable evidence contract.

---

## 18. Adapter protocol sketch

```python
class OpenShellExecutionEngine:
    name = "openshell"
    capability_class = "sandbox_execution"

    def supports(self, capability: str) -> bool:
        # True only for capabilities backed by the current qualification record.
        ...

    def health(self) -> EngineHealth:
        ...

    def execute(
        self,
        task: TaskSpec,
        context: ContextAssembly,
    ) -> EngineResult:
        request = compile_execution_request(task, context)
        enforce_residual_admission(request)
        sandbox = ensure_bound_sandbox(request)
        evidence = run_and_collect(sandbox, request)
        return normalize_result(evidence)
```

The adapter MUST NOT derive new authority from `supports()`, `health()`, or vendor success responses.

---

## 19. Acceptance criteria for this specification

The R0 spec is ready for implementation when review confirms:

1. no v1 release dependency is introduced;
2. the RESIDUAL/OpenShell authority split is explicit;
3. credentials never need to transit RESIDUAL as plaintext to launch an agent;
4. exact policy and workload identities can be bound to evidence or marked unavailable;
5. compute-driver qualification is tuple-scoped;
6. Hermes/OpenClaw use does not make NemoClaw the universal adapter contract;
7. artifact admission remains independent of sandbox success;
8. retries preserve first-failure evidence;
9. the first self-build lane cannot merge to accepted main by itself;
10. the qualification plan in `QUAL-ADAPTER-OPENSHELL-R0.md` can produce a deterministic verdict.

---

## 20. Upstream assumptions to revalidate at qualification time

The qualification runner MUST revalidate current upstream behavior before execution because OpenShell/NemoClaw are evolving projects.

At the time this R0 was authored, upstream documentation described:

- a gateway/sandbox split with the gateway owning durable control-plane state and the supervisor enforcing local sandbox semantics;
- sandbox policies controlling filesystem, network, process identity, and request behavior;
- provider credentials represented to the agent by placeholders and resolved by a proxy only under policy/binding constraints;
- Docker, Podman, Kubernetes, and VM-class compute drivers, with driver-specific support boundaries;
- NemoClaw-managed Hermes and OpenClaw paths above OpenShell;
- upstream support limitations that vary by agent/platform.

These are **inputs to qualification, not permanent RESIDUAL facts**. If current upstream behavior differs, the qualification MUST stop and this spec MUST be reconciled before claiming PASS.

---

## 21. Post-v1 sequencing

Recommended order after v1 convergence:

1. freeze exact RESIDUAL release identity;
2. run `RESIDUAL-PERF` production-envelope / verification-tax work as planned;
3. implement the OpenShell R0 contracts and pure policy compiler;
4. execute Docker/direct OpenShell qualification;
5. execute NemoClaw/Hermes qualification;
6. execute NemoClaw/OpenClaw qualification;
7. add a machine-readable provider/driver qualification matrix;
8. run the bounded "RESIDUAL builds RESIDUAL" fixture lane;
9. only then consider credentialed repository-write or broader fleet deployment capabilities.

This sequence MAY be parallelized where it does not change v1 closure or accepted release criteria.


---

## 22. Upstream reference set used for R0

These URLs are informative references only. Qualification MUST re-check the exact upstream release being tested.

- OpenShell sandbox policy overview: https://docs.nvidia.com/openshell/dev/how-it-works/policies/overview
- OpenShell provider/credential model: https://docs.nvidia.com/openshell/sandboxes/manage-providers
- OpenShell compute-driver reference: https://docs.nvidia.com/openshell/dev/reference/sandbox-compute-drivers
- OpenShell supported agents: https://docs.nvidia.com/openshell/about/supported-agents
- OpenShell project: https://github.com/NVIDIA/OpenShell
- NemoClaw Hermes platform support: https://docs.nvidia.com/nemoclaw/user-guide/hermes/reference/platform-support
- NemoClaw/OpenShell CLI selection and ownership guidance: https://docs.nvidia.com/nemoclaw/user-guide/hermes/reference/cli-selection-guide
- NemoClaw project: https://github.com/NVIDIA/NemoClaw

When a reference path moves or disappears, that is not evidence that the old behavior still applies. Q0 MUST resolve the current documentation/API surface and record the replacement reference.
