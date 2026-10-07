# Residual Command Station — Structural Resilience Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-command-station v1.0.0 → v2.0.0
**Depends on:** WORLD_CLASS_SPECS.md, NETOPS_SECOPS_SPECS.md, SPECS.md

---

## Overview

Five foundational layers that make the station resilient against:
shifting cryptographic standards, changing AI architectures, scaling
infrastructure complexity, environmental drift, and multi-station
deployment. Each layer is specified independently but designed to
compose.

---

## Layer 1: Post-Quantum Cryptographic Agnosticism

### Purpose
Decouple all cryptographic primitives into a pluggable module layer
so the station can transition to post-quantum algorithms without
rewriting core execution logic.

### The Problem
SHA-256, HMAC-SHA256, ECDSA, and RSA are vulnerable to Shor's
algorithm (signatures) and Grover's algorithm (hashes, quadratic
speedup only). The station's hash chains, receipt bindings, TPM
extensions, and HITL signatures all depend on these primitives.

### The CryptoProvider Protocol

```python
class CryptoProvider(Protocol):
    """Pluggable cryptographic primitive provider."""

    name: str                    # "sha256", "sha3-256", "dilithium", ...
    security_level: int          # classical bits of security

    # Hashing
    def hash(self, data: bytes) -> bytes: ...
    def hash_hex(self, data: bytes) -> str: ...

    # Keyed hashing / commitments
    def mac(self, key: bytes, data: bytes) -> bytes: ...
    def mac_hex(self, key: bytes, data: bytes) -> str: ...

    # Digital signatures
    def sign(self, private_key: bytes, data: bytes) -> bytes: ...
    def verify(self, public_key: bytes, data: bytes, signature: bytes) -> bool: ...

    # Key encapsulation (for future encrypted channels)
    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]: ...  # (shared_secret, ciphertext)
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes: ...
```

### Requirements

**PQC-R1.** Every hash computation in the station MUST go through
the active `CryptoProvider`. No module MAY call `hashlib.sha256()`
directly. The `hashlib` import MUST appear in exactly one file: the
crypto provider implementation.

**PQC-R2.** The `CryptoProvider` MUST be injectable at station
construction. The default MUST be `SHA256Provider` (classical). A
`DilithiumProvider` and `SPHINCSPlusProvider` MUST be available but
MUST NOT be default until NIST standardization is complete and
library support is production-grade.

**PQC-R3.** Receipt hashes, cache keys, observation chain hashes,
quarantine fingerprints, and HITL signatures MUST all use the active
provider. Changing the provider MUST change all hashes — this is
intentional and correct. A station running Dilithium produces
different hashes than a station running SHA-256. Cross-station
receipt verification MUST include the provider name in the
verification context.

**PQC-R4.** The `CryptoProvider` interface MUST NOT expose algorithm
specifics above the protocol. Callers MUST NOT know whether they are
using SHA-256 or SHA3-256 or a lattice-based hash. The interface
is algorithm-agnostic by design.

**PQC-R5.** TPM integration (Frontier 3 from WORLD_CLASS_SPECS.md)
MUST use the active `CryptoProvider` for PCR extend operations. If
the TPM does not support the active algorithm, the TPM sink MUST
degrade gracefully to software-only hashing with
`hardware_rooted: false`.

**PQC-R6.** Key lengths, signature sizes, and hash output sizes MUST
NOT be hardcoded anywhere outside the crypto provider. The station
MUST be size-agnostic.

**PQC-R7.** A `CryptoMigrationPlan` MUST be defined for any running
station. The plan MUST specify: current provider, target provider,
migration trigger (date, security advisory, or manual), and
receipt re-signing strategy. Receipts signed under the old provider
MUST remain verifiable under the old provider's public keys after
migration.

### Migration Path

```
Phase 1: SHA256Provider (current, default)
Phase 2: HybridProvider — signs with both classical and PQC,
         verifies with either. Receipts carry dual signatures.
Phase 3: DilithiumProvider (post-migration, when NIST PQC is
         production-ready and TPM 2.0 spec supports PQC algorithms)
```

---

## Layer 2: Model-Agnostic Reasoning Interface

### Purpose
Decouple the station from transformer-specific text-in/text-out APIs.
Treat the agent as a black-box state transformer that emits typed
intention vectors regardless of the underlying architecture.

### The Problem
Current provider interface assumes: messages in → text out → parse
for tool calls. This breaks for:
- State-space models (Mamba) with different state management
- Diffusion-based code synthesizers that generate holistically
- Test-time compute models that reason internally before responding
- Optimization solvers (CP-SAT, SMT) that return structured solutions

### The ReasoningEngine Protocol

```python
class ReasoningEngine(Protocol):
    """Model-agnostic reasoning interface."""

    name: str                    # engine identifier
    capability_class: str        # "generative", "solver", "hybrid"

    def reason(self, state: ReasoningState) -> IntentionVector: ...

    def supports(self, capability: str) -> bool: ...
    # capabilities: "tool_calling", "structured_output",
    #               "streaming", "multi_turn", "planning"


@dataclass(frozen=True)
class ReasoningState:
    """What the engine sees. Not necessarily text."""
    goal: GoalSpec
    context: ContextAssembly
    prior_intentions: tuple[IntentionVector, ...]
    observation_window: tuple[Observation, ...]


@dataclass(frozen=True)
class IntentionVector:
    """What the engine wants to do. Typed, not parsed from text."""
    intentions: tuple[Intention, ...]
    confidence: float
    reasoning_trace_hash: Optional[str] = None  # if engine provides one


@dataclass(frozen=True)
class Intention:
    kind: str                    # "tool_call", "respond", "request_info", "propose_change"
    target: str                  # tool name, file path, etc.
    arguments: dict[str, Any]
    rationale: Optional[str] = None
```

### Requirements

**MAI-R1.** The `ReasoningEngine` protocol MUST be the sole interface
between the station and any model. The existing `Provider` protocol
(from ai_providers) MUST be adapted to `ReasoningEngine` via a
wrapper. No station code MAY call a provider directly.

**MAI-R2.** `IntentionVector` MUST be typed and structured. The
station MUST NOT parse tool calls from raw text. Text parsing is the
adapter's job, not the station's.

**MAI-R3.** The `reason()` method MUST be synchronous. The station's
synchronous constraint applies to all engines. An engine that requires
async MUST be wrapped with a sync bridge that blocks until complete.

**MAI-R4.** Engines that do not support `tool_calling` MUST NOT be
used for tasks that require tool use. The station MUST check
`supports("tool_calling")` before assigning a task to an engine.

**MAI-R5.** The `reasoning_trace_hash` field MUST be optional. Engines
that cannot provide a trace (diffusion models, solvers) MUST NOT be
penalized. The station MUST NOT require chain-of-thought from any
engine.

**MAI-R6.** A `SolverEngineAdapter` MUST be provided for optimization
solvers (Z3, CP-SAT, OR-Tools). The adapter converts the ReasoningState
into a solver problem definition and converts the solver's solution
into an IntentionVector with `kind: "propose_change"`.

**MAI-R7.** The existing Ollama/OpenAI/Anthropic adapters MUST be
wrapped as `GenerativeEngineAdapter` instances that implement
`ReasoningEngine`. The wrapper handles: messages → ReasoningState,
response → IntentionVector.

---

## Layer 3: Formal Methods & Program-Synthesized Verifiers

### Purpose
Replace hand-written verifier code with formally verified or
program-synthesized correctness invariants.

### The Problem
Manual Python verifiers have blind spots. A NetOps stabilization check
might miss a corner case. A SecOps pattern might not cover a new
exfiltration vector. Formal verification eliminates verifier bugs.

### Architecture

```
High-level goal description
        │
        ▼
┌─────────────────────────────┐
│  Specification Compiler     │
│  (goal → formal invariant)  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Theorem Prover (Z3/Lean)   │
│  (invariant → proof or      │
│   counterexample)           │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Verified Verifier          │
│  (mechanical check that     │
│   evaluates the invariant)  │
└─────────────────────────────┘
```

### Requirements

**FMV-R1.** The station MUST support two verifier classes:
`HandWrittenVerifier` (current, Python callable) and
`FormalVerifier` (compiled from a formal specification). Both MUST
implement the same `Evaluator` protocol.

**FMV-R2.** A `FormalVerifier` MUST carry a proof certificate. The
certificate MUST be verifiable independently of the station. The
verifier MUST NOT be registered without a valid certificate.

**FMV-R3.** The specification compiler MUST be a separate tool, not
a runtime component. Compilation happens at task definition time,
not at execution time. The compiled verifier is a static artifact.

**FMV-R4.** If the theorem prover returns `unknown` or `timeout`
(cannot prove or disprove the invariant), the compiler MUST NOT
emit a verifier. The task MUST fall back to `HandWrittenVerifier`
with a `formal_verification: "not_proven"` flag in the receipt.

**FMV-R5.** Formal verifiers MUST be preferred over handwritten
verifiers for the same check. If both are registered for the same
criterion, the formal verifier MUST be selected and the handwritten
verifier MUST be recorded as `superseded_by` in the receipt.

**FMV-R6.** The proof certificate MUST be content-addressed and
stored alongside the verifier. The certificate hash MUST be included
in the receipt's `verifier_revision` field, binding the proof to
the execution.

---

## Layer 4: Autonomous Policy Auto-Calibration

### Purpose
Detect environmental drift and re-baseline safety thresholds
autonomously, requiring human sign-off only for structural changes.

### The Problem
Static thresholds decay. A NetOps packet-loss threshold of 2% might
be normal for one network and catastrophic for another. A SecOps
vulnerability count that was acceptable last year might not be today.

### Architecture

```
Telemetry observations
        │
        ▼
┌─────────────────────────────┐
│  Drift Detector             │
│  (statistical process       │
│   control on metric         │
│   distributions)            │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Calibration Engine         │
│  (proposes new threshold    │
│   based on historical       │
│   distribution)             │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Change Classifier          │
│  (parametric vs structural) │
└─────────────┬───────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
Parametric          Structural
(auto-applied,      (HITL challenge,
 observed)          human signature
                     required)
```

### Requirements

**APC-R1.** The drift detector MUST use statistical process control
(Westgard rules or equivalent) on observed metric distributions. It
MUST NOT use simple threshold comparisons for drift detection.

**APC-R2.** A threshold change is `parametric` if it stays within
the same metric family and does not change the check type. A change
is `structural` if it: adds/removes a check, changes a check type,
or modifies the GoalSpec success criteria ordering.

**APC-R3.** Parametric changes MUST be auto-applied. They MUST be
observed with `event: policy_parametric_change`, including old value,
new value, statistical justification, and confidence interval.

**APC-R4.** Structural changes MUST generate a HITL challenge per
HITL-R1 through HITL-R8 from WORLD_CLASS_SPECS.md. They MUST NOT be
auto-applied under any circumstances.

**APC-R5.** The calibration engine MUST NOT reduce safety margins
without historical evidence. A proposed threshold that is more
permissive than the current threshold MUST require a minimum of
30 days of observation data supporting the change.

**APC-R6.** All calibration proposals MUST be recorded in the
epistemic memory store with their statistical justification, even
if rejected. Rejected proposals MUST include the rejection reason.

**APC-R7.** The calibration engine MUST NOT modify the
`verifier_revision` field directly. It MUST propose a new revision
to the module owner. The module owner increments the revision,
which triggers cache invalidation per VRB-R3.

---

## Layer 5: Federated Multi-Station Trust Meshes

### Purpose
Enable independent stations in different data centers to
cryptographically verify and merge state changes without sharing
raw operational data.

### Architecture

```
Station A (US-East)          Station B (EU-Central)
┌──────────────┐             ┌──────────────┐
│ Local DAG    │             │ Local DAG    │
│ Local ledger │             │ Local ledger │
│ Local receipt│             │ Local receipt│
└──────┬───────┘             └──────┬───────┘
       │                            │
       ▼                            ▼
┌─────────────────────────────────────────┐
│         Federation Gateway              │
│  (receipt exchange, CRDT merge,         │
│   zk-attestation of local state)        │
└─────────────────────────────────────────┘
```

### Requirements

**FED-R1.** Each station in a federation MUST retain full local
sovereignty. No station MAY read another station's observation log,
quarantine store, or epistemic memory directly.

**FED-R2.** Stations MUST exchange receipts, not raw data. A receipt
proves a task was executed and verified without revealing the task's
inputs, outputs, or intermediate state.

**FED-R3.** Receipt exchange MUST use the active `CryptoProvider`
for signing and verification. Cross-station verification MUST include
the provider name and public key fingerprint in the verification
context.

**FED-R4.** Conflicting receipts (same task_id, different verdicts)
MUST be resolved by the receiving station's local verifier. The
receiving station MUST NOT trust the sending station's verdict.
It MUST re-execute the verification locally using the receipt's
bound verifier name and revision.

**FED-R5.** Epistemic CRDTs (Frontier 4 from WORLD_CLASS_SPECS.md)
MUST be used for merging non-conflicting state. The CRDT merge
function MUST be proven commutative, associative, and idempotent
before federation deployment.

**FED-R6.** A station MUST be able to join and leave a federation
without disrupting other stations. Joining requires: cryptographic
identity establishment, receipt format agreement, and CRDT schema
alignment. Leaving requires: final receipt flush and CRDT state
snapshot.

**FED-R7.** Federation membership MUST be observed. Join, leave, and
receipt exchange events MUST emit `checkpoint` observations with
the remote station's identity and the exchanged receipt hashes.

**FED-R8.** A compromised station MUST be revocable by federation
consensus. Revocation MUST invalidate all future receipts from the
compromised station. Past receipts MUST remain verifiable against
the compromised station's pre-revocation public keys.

---

## Composition Matrix

| Layer | Depends On | Enables |
|---|---|---|
| PQC Agnosticism | Nothing (foundation) | All cryptographic operations |
| Model-Agnostic Interface | Nothing (parallel foundation) | All model interactions |
| Formal Verifiers | Model-Agnostic Interface | Verified correctness |
| Policy Auto-Calibration | Formal Verifiers, Epistemic Memory | Drift resilience |
| Federated Meshes | PQC, CRDTs, Receipt Binding | Multi-station deployment |

**Build order:** PQC and Model-Agnostic in parallel (both are
interface extractions). Formal Verifiers next. Auto-Calibration
after Formal Verifiers (needs verified invariants to calibrate
against). Federation last (needs all other layers stable).
