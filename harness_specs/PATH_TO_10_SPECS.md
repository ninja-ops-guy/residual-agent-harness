# Residual Command Station — Path to 9+ and 10 Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-agent-harness v1.0.0 → v2.0.0
**Depends on:** M2_M3_M4_SPECS.md, STUDIO_SPECS.md, all previous specs

---

## Overview

Two milestone specs. SPEC-NINE covers the path from 8.5 to 9.5:
engine adapters, production soak, async I/O, cluster layer,
documentation. SPEC-TEN covers the path from 9.5 to 10: published
research, production at scale, ecosystem, zk-proofs/TEE, formal
verification.

---

## SPEC-NINE: Path to 9.5

### Purpose
Close the five gaps between current state (8.5) and world-class
platform (9.5). Each gap is independently valuable. Together they
transform Residual from "architecturally correct" to "production
proven."

---

### SPEC-NINE-001: Engine Adapter Implementation

**Current state:** SPEC-ECO-001 through SPEC-ECO-004 define the
ExecutionEngine protocol. No adapters exist.

**Requirements**

**N9-R1.** A `residual/engines/` module MUST be created with:
- `protocol.py` — ExecutionEngine, EngineResult, TaskSpec
- `router.py` — CapabilityRouter with probe validation
- `langgraph_adapter.py` — LangGraph ExecutionEngine
- `crewai_adapter.py` — CrewAI ExecutionEngine
- `sdk_adapter.py` — Claude SDK and OpenAI Assistants adapters
- `probe.py` — Capability validation probe suite

**N9-R2.** The LangGraph adapter MUST accept a LangGraph StateGraph
without modification. It MUST convert TaskSpec to LangGraph input,
execute via `invoke()`, and normalize the output state to
EngineResult. It MUST NOT modify the graph's internal structure.

**N9-R3.** The CrewAI adapter MUST disable CrewAI's internal HITL.
CrewAI's `human_input` parameter MUST be set to False. Residual's
HITL gateway is the sole human-in-the-loop path.

**N9-R4.** SDK adapters MUST treat SDK safety features as advisory.
If the SDK refuses a task that Residual's policies permit, the
refusal MUST be recorded but MUST NOT block execution. If the SDK
permits a task that Residual's policies deny, Residual's denial
MUST prevail.

**N9-R5.** The CapabilityRouter MUST validate claimed capabilities
with a probe suite before trusting them. The probe suite MUST test:
- Can the engine accept a TaskSpec?
- Can the engine produce a normalizable output?
- Does the engine respect token budgets?
- Does the engine crash gracefully?

**N9-R6.** Engine adapters MUST run in isolated processes. The
adapter is the sandbox boundary. Residual sends TaskSpec and
ContextAssembly in, receives EngineResult out.

**N9-R7.** The receipt MUST record which engine executed the task.
Receipt fields: `engine_name: str`, `engine_version: str`.

**N9-R8.** A proof-of-concept integration MUST exist: a LangGraph
graph wrapped as an ExecutionEngine, executing a task through
Residual's full pipeline (GoalSpec → Quarantine → Verify → Receipt),
with the IntegrationReceipt proving end-to-end correctness.

---

### SPEC-NINE-002: Production Soak Test

**Current state:** 276 tests passing. No real-world deployment
validation.

**Requirements**

**N9-R9.** A 30-day continuous soak test MUST be executed against
real infrastructure. The soak test MUST:
- Run 24/7 for 30 consecutive days
- Execute at least 1000 tasks per day
- Include NetOps and SecOps operational tasks
- Include intentional failures (bad configs, missing dependencies)
- Include adversarial inputs (injection attempts, contract violations)

**N9-R10.** The soak test MUST produce a signed SoakTestReport
containing:
- Total tasks executed, accepted, rejected, escalated
- Zero unhandled exceptions (any exception = test failure)
- Cache hit rate (target: ≥ 60%)
- Token savings (target: ≥ 40% vs uncached)
- Brake false positive rate (target: ≤ 5%)
- Brake false negative rate (target: ≤ 1%)
- HITL escalation rate (target: ≤ 10%)
- Mean time to recovery from intentional failures

**N9-R11.** The SoakTestReport MUST be cryptographically signed
by the Station's identity key. It MUST be suitable for publication
as evidence of production readiness.

**N9-R12.** The soak test MUST include at least one red team
exercise: a dedicated adversary attempting to bypass quarantine,
forge receipts, trigger unsafe execution, or exfiltrate data.
The exercise MUST be observed. Every attempt MUST produce a
receipt. The report MUST document which attacks succeeded and
which were blocked.

---

### SPEC-NINE-003: Async I/O Integration

**Current state:** Synchronous constraint applies to everything.
Network I/O blocks verification.

**Requirements**

**N9-R13.** Network I/O MUST be async. Verification MUST remain
synchronous. The boundary: async code fetches data, synchronous
code verifies it.

**N9-R14.** The async periphery MUST NOT block the synchronous
core. If a telemetry fetch takes 30 seconds, the LoopController
MUST NOT wait. The verifier receives the most recent cached
telemetry and marks the check UNKNOWN if the cache is stale
beyond `max_telemetry_age_s`.

**N9-R15.** Async tasks MUST be cancellable. When a run aborts,
all pending async I/O MUST be cancelled within 5 seconds.

**N9-R16.** The observation sink MUST buffer events and flush
asynchronously. Synchronous emission MUST NOT block on I/O. The
buffer MUST be durable up to `buffer_capacity` events.

**N9-R17.** A `residual/async_io/` module MUST be created:
- `telemetry.py` — AsyncTelemetryClient with staleness detection
- `sink.py` — AsyncObservationSink with buffered flush
- `server.py` — Async HTTP server for HITL and station API

---

### SPEC-NINE-004: Cluster Layer

**Current state:** Mesh module exists with in-memory message
passing. No wire protocol, no LAN discovery, no GPU pooling.

**Requirements**

**N9-R18.** A wire protocol MUST be implemented for mesh
communication. The protocol MUST support:
- Device discovery (mDNS for LAN, WebSocket relay for WAN)
- Capability announcement (model names, tok/s, context window)
- Task assignment and result return
- Receipt exchange and verification
- Device join and leave

**N9-R19.** A `residual node join` CLI command MUST exist. It MUST:
discover the cluster, authenticate with the cluster key, announce
capabilities, and begin accepting tasks.

**N9-R20.** A `residual node leave` CLI command MUST exist. It MUST:
finish in-flight tasks, announce departure, and remove itself from
the routing table.

**N9-R21.** The cluster MUST handle node failure gracefully. If a
node becomes unresponsive, the cluster MUST reassign its in-flight
tasks to other capable nodes. The failed node's receipts MUST be
marked `node_failed` and excluded from integration.

**N9-R22.** The cluster MUST display aggregate capacity: total GPUs,
total models, total workers, total memory. This MUST be visible in
the IDE cluster panel and via CLI (`residual cluster status`).

**N9-R23.** Task routing across the cluster MUST prefer local nodes
when capability is equal. Cloud nodes MUST be selected for capability
gaps or when local capacity is exhausted.

---

### SPEC-NINE-005: Documentation and Onboarding

**Current state:** Internal architecture docs are excellent. No
onboarding path for new users.

**Requirements**

**N9-R24.** A quickstart guide MUST exist at `docs/quickstart.md`.
It MUST take a user from `pip install residual-command-station`
to a running task in under 10 minutes. It MUST include:
- Installation (pip and Docker)
- Starting a local Ollama model
- Running a simple task through the CLI
- Viewing the receipt in the web UI

**N9-R25.** A module development tutorial MUST exist at
`docs/module-tutorial.md`. It MUST cover:
- Implementing StationModule
- Writing quarantine policies
- Writing verifiers
- Writing brakes
- Testing with the validation suite
- Publishing to the module marketplace

**N9-R26.** Three reference architectures MUST be documented:
- `docs/architecture/ci-cd.md` — CI/CD pipeline integration
- `docs/architecture/incident-response.md` — NetOps remediation
- `docs/architecture/compliance-audit.md` — SecOps evidence collection

**N9-R27.** All documentation code examples MUST be executable and
MUST pass in CI. Stale documentation is worse than no documentation.

**N9-R28.** A `docs/faq.md` MUST exist covering:
- "Why is my task stuck in quarantine?"
- "How do I add a new model provider?"
- "How do I debug a brake trip?"
- "How do I escalate to a human?"
- "How do I write a custom module?"

---

## SPEC-TEN: Path to 10

### Purpose
Close the five gaps between world-class platform (9.5) and
legendary system (10). These require time, ecosystem growth,
and research breakthroughs.

---

### SPEC-TEN-001: Published Research

**Current state:** Evaluation framework exists. No published results.

**Requirements**

**T10-R1.** The FrozenWorkload evaluation (single vs fixed vs
dynamic swarm) MUST be executed with n ≥ 10 runs per configuration.
Results MUST include mean, median, standard deviation, and
statistical significance tests.

**T10-R2.** The evaluation MUST be published in a peer-reviewed
venue. Suitable venues include:
- NeurIPS (AI for Systems track)
- OSDI (Operations track)
- SOSP (Systems track)
- USENIX Security (if emphasizing SecOps)
- A top-tier software engineering venue (ICSE, FSE)

**T10-R3.** The publication MUST include:
- Full system architecture description
- FrozenWorkload definition
- All raw evaluation data (as supplementary material)
- Statistical analysis
- Comparison to existing systems (LangGraph, CrewAI, etc.)
- Honest discussion of limitations

**T10-R4.** The publication MUST be reproducible. A reviewer MUST
be able to clone the repo, run the evaluation, and verify the
results. The FrozenWorkload, all configurations, and the
evaluation harness MUST be in the repo.

---

### SPEC-TEN-002: Production Deployment at Scale

**Current state:** No production deployment beyond the developer's
own infrastructure.

**Requirements**

**T10-R5.** At least one production deployment MUST exist at a
organization with ≥ 100 employees. The deployment MUST:
- Run Residual for compliance-critical operations
- Process ≥ 100 tasks per day
- Have been running for ≥ 90 days
- Have a named operator responsible for it

**T10-R6.** A case study MUST be published documenting the
production deployment. The case study MUST include:
- Organization type (anonymized if necessary)
- Use case description
- Tasks executed and outcomes
- Measurable benefits (time saved, errors prevented, costs reduced)
- Challenges encountered and how they were resolved

**T10-R7.** The production deployment MUST produce evidence
suitable for a reference customer. A potential adopter MUST be
able to contact the reference customer (directly or through
Residual) to discuss their experience.

---

### SPEC-TEN-003: Ecosystem Growth

**Current state:** Zero third-party modules. Zero community.

**Requirements**

**T10-R8.** At least 10 third-party modules MUST exist on the
module marketplace. Modules MUST cover diverse domains:
- At least 2 infrastructure modules (NetOps variants)
- At least 2 security modules (SecOps variants)
- At least 2 data engineering modules
- At least 2 testing/QA modules
- At least 2 domain-specific modules (finance, healthcare, etc.)

**T10-R9.** At least 3 engine adapters MUST be maintained by
parties other than the core Residual team. These MUST include
at least one adapter for a framework not originally supported
(e.g., AutoGen, Semantic Kernel, Haystack).

**T10-R10.** A community forum or Discord server MUST exist with
≥ 100 active members. Active means: has posted in the last 30 days.

**T10-R11.** At least 3 external contributors MUST have commit
access to the main repository. External means: not employed by
or financially dependent on the core team.

---

### SPEC-TEN-004: Cryptographic Cloud Execution

**Current state:** HMAC commitment wrapper exists. No zk-proofs,
no TEE integration.

**Requirements**

**T10-R12.** A Trusted Execution Environment (TEE) integration
MUST be implemented. Supported TEEs MUST include at least one of:
- AWS Nitro Enclaves
- Intel SGX
- AMD SEV-SNP

**T10-R13.** When a task escalates to a cloud provider running
in a TEE, the station MUST receive an attestation document from
the TEE. The attestation MUST be verified against the TEE
manufacturer's root certificate.

**T10-R14.** The attestation MUST be bound into the receipt. A
receipt for a TEE-executed task MUST include:
- TEE type (nitro, sgx, sev)
- Attestation document hash
- Measurement (MRENCLAVE, MRTD, or equivalent)
- Verification timestamp

**T10-R15.** If zk-SNARK or zk-STARK proving becomes practical
for verifier circuits, a zk-proof integration MAY replace TEE
attestation. Until then, TEE attestation is the production path.
The documentation MUST NOT claim "zero knowledge" for TEE-based
attestation. It MUST be labeled "attested execution."

---

### SPEC-TEN-005: Formal Verification

**Current state:** Verifiers are hand-written Python. No formal
proofs.

**Requirements**

**T10-R16.** A specification compiler MUST be built. The compiler
MUST accept a high-level requirement description and produce:
- A formal invariant (Z3, Lean, or equivalent)
- A proof obligation
- A verified checker (if proof succeeds)

**T10-R17.** The specification compiler MUST be a separate tool,
not a runtime component. Compilation happens at task definition
time, not execution time.

**T10-R18.** If the theorem prover returns `unknown` or `timeout`,
the compiler MUST NOT emit a verified checker. The task MUST fall
back to hand-written verifiers with a `formal_verification:
"not_proven"` flag in the receipt.

**T10-R19.** At least one critical path MUST be formally verified.
Suitable candidates:
- NetOps BGP config validation (prove no routing loops)
- SecOps secret detection (prove no false negatives for known patterns)
- Receipt chain validation (prove no forgery possible)

**T10-R20.** The formal verification artifact (proof certificate)
MUST be content-addressed and stored alongside the verifier. The
certificate hash MUST be included in the receipt's
`verifier_revision` field.

---

## Implementation Timeline

| Milestone | Spec | Effort | Dependencies |
|---|---|---|---|
| N9-001 | Engine Adapters | 4 weeks | None |
| N9-002 | Production Soak | 6 weeks (parallel) | None |
| N9-003 | Async I/O | 3 weeks | None |
| N9-004 | Cluster Layer | 6 weeks | Async I/O |
| N9-005 | Documentation | 3 weeks (parallel) | Engine Adapters |
| **v1.0.0** | **9.5 rating** | **~12 weeks** | All N9 |
| T10-001 | Published Research | 12 weeks | v1.0.0 + evaluation |
| T10-002 | Production at Scale | 12+ weeks | v1.0.0 |
| T10-003 | Ecosystem Growth | 26+ weeks | v1.0.0 |
| T10-004 | TEE Integration | 8 weeks | v1.0.0 |
| T10-005 | Formal Verification | 12+ weeks | v1.0.0 |
| **v2.0.0** | **10 rating** | **~52 weeks** | All T10 |

---

## The Honest Path

The path to 9.5 is engineering: build the adapters, run the soak,
write the docs. It's 12 weeks of focused work.

The path to 10 is time and luck: publish the research, find the
reference customer, grow the community, land the TEE integration,
prove the formal verifiers. It's 52 weeks minimum, and some of it
is outside your control.

The 9.5 is achievable. The 10 is aspirational. Both are worth
building toward.
