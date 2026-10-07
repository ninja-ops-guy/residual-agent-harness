# Residual Command Station — Federated Group Chat Mesh Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-command-station v1.0.0+
**Depends on:** RESILIENCE_SPECS.md (Layer 5), WORLD_CLASS_SPECS.md (Part 4 Frontier 4)

---

## 1. Purpose

Enable multiple devices, each running Residual Command Station with
local models (Ollama), to form a federated group chat. Any device can
pose a task. Any device can contribute compute. All devices see the
same conversation. No device reveals its local data unless explicitly
shared.

---

## 2. Architecture

```
Device A (laptop)          Device B (desktop)         Device C (server)
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│ Ollama: llama3  │        │ Ollama: qwen2   │        │ Ollama: mistral │
│ Station: active │        │ Station: active │        │ Station: active │
│ Chat UI: joined │◄──────►│ Chat UI: joined │◄──────►│ Chat UI: joined │
└─────────────────┘        └─────────────────┘        └─────────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                            ┌───────┴───────┐
                            │  Mesh Relay   │
                            │  (optional)   │
                            │  WebSocket    │
                            └───────────────┘
```

Two modes:
- **LAN mode:** Direct peer-to-peer via mDNS discovery. No relay.
- **WAN mode:** WebSocket relay for NAT traversal. Relay sees only
  encrypted envelopes, never plaintext.

---

## 3. Core Concepts

### 3.1 Mesh Identity

Each device has a `MeshIdentity`:
```python
@dataclass(frozen=True)
class MeshIdentity:
    device_id: str          # UUID, generated on first run
    display_name: str       # human-readable, user-set
    public_key: bytes       # X25519 or Dilithium public key
    capabilities: tuple[str, ...]  # model names, tool types
    address: str            # LAN IP:port or relay address
    joined_at_ns: int
```

### 3.2 Chat Message

Every message in the group chat is a `MeshMessage`:
```python
@dataclass(frozen=True)
class MeshMessage:
    message_id: str         # UUID
    author_id: str          # MeshIdentity.device_id of sender
    timestamp_ns: int
    kind: str               # "chat", "task_proposal", "task_result",
                            # "model_offer", "model_response", "receipt"
    content: str            # human-readable text (for chat kind)
    payload: dict           # structured data (for task/result kinds)
    signature: bytes        # signed by author_id's private key
```

### 3.3 Task Flow

```
Device A proposes task
        │
        ▼
MeshMessage(kind="task_proposal", payload={goal_spec, ...})
        │
        ▼
All devices receive proposal
        │
        ▼
Devices with suitable models respond:
MeshMessage(kind="model_offer", payload={model_name, capability_score})
        │
        ▼
Proposer selects best offer (or lets mesh consensus decide)
        │
        ▼
Selected device executes task via its local station
        │
        ▼
Result broadcast:
MeshMessage(kind="task_result", payload={result, receipt_hash})
        │
        ▼
All devices verify receipt against their local verifier
```

---

## 4. Requirements

### 4.1 Discovery

**MESH-R1.** Devices MUST discover each other automatically on LAN
via mDNS (`_residual._tcp.local.`). No manual configuration required
for LAN mode.

**MESH-R2.** Devices MUST announce their capabilities (model names,
tool types, available compute) in the mDNS TXT record. Capability
announcement MUST NOT include model weights, fine-tuning data, or
any local file contents.

**MESH-R3.** For WAN mode, devices MUST connect to a relay via
WebSocket. The relay MUST NOT decrypt message contents. End-to-end
encryption between devices is mandatory.

**MESH-R4.** A device MUST be able to join and leave the mesh at any
time without disrupting other devices. Joining emits a
`mesh.device_joined` observation. Leaving emits `mesh.device_left`.

### 4.2 Messaging

**MESH-R5.** All mesh messages MUST be signed by the sender's private
key. Receiving devices MUST verify signatures before processing.

**MESH-R6.** Chat messages (kind="chat") MUST be human-readable text.
They MUST NOT contain executable code, tool calls, or structured data.
Code and structured data belong in payload fields of non-chat kinds.

**MESH-R7.** Task proposals MUST include a complete GoalSpec. The
GoalSpec MUST be frozen before broadcast. Amendments follow the
existing amendment protocol (SPEC-001-R7).

**MESH-R8.** Model offers MUST include: model name, quantization level,
context window size, and a capability score (0.0-1.0) self-assessed by
the offering device. Capability scores MUST be advisory; the proposer
makes the final selection.

### 4.3 Task Execution

**MESH-R9.** The device executing a task MUST run it through its local
station: GoalSpec → LoopController → QuarantineStore → Verifier. The
full v0.3.0+ pipeline applies.

**MESH-R10.** The executing device MUST broadcast the result as a
`task_result` message containing: the final response, the receipt hash,
the verifier revision used, and the RunOutcome.

**MESH-R11.** All receiving devices MUST verify the receipt hash
against their local verifier registry. If the verifier is not
registered locally, the receipt MUST be marked `unverifiable` and the
result MUST NOT be accepted as verified.

**MESH-R12.** If any device disputes a result (receipt verification
fails, verifier revision mismatch, or GoalSpec hash mismatch), the
dispute MUST be broadcast as a `task_result_dispute` message. The
dispute MUST include the reason and the locally computed expected hash.

**MESH-R13.** Disputed results MUST NOT enter the shared conversation
history as verified. They MAY enter as disputed, clearly marked.

### 4.4 Local Model Contribution

**MESH-R14.** A device offering a local model MUST ensure the model
is loaded and ready before sending the offer. An offer for an
unloaded model that would require >30 seconds to load MUST include
`load_time_estimate_s` in the offer payload.

**MESH-R15.** Local models execute tasks on the offering device. Model
weights, training data, and local files MUST NOT leave the device.
Only the task inputs (from the GoalSpec and declared evidence) and
the result outputs cross the device boundary.

**MESH-R16.** The disclosure lattice applies to mesh tasks. A task
that requires evidence marked `local_only` on the executing device
MUST be denied by that device's quarantine store. The denial MUST be
broadcast as a `task_denied` message with reason
`disclosure_lattice_violation`.

**MESH-R17.** Devices MAY decline tasks. Declination MUST NOT require
a reason. A device that declines MUST NOT appear in the offer list
for that task.

### 4.5 Group Chat Semantics

**MESH-R18.** The group chat MUST have a shared, append-only message
log. Every device MUST maintain a local copy. Messages MUST be
ordered by timestamp_ns. Ties broken by message_id lexicographic
order.

**MESH-R19.** The shared message log MUST be hash-chained. Each
message's hash includes the previous message's hash. This chain
MUST be independent of the observation layer's chain — it is a
separate, chat-specific chain.

**MESH-R20.** If two devices produce conflicting message chains
(different messages at the same position), the chain with the
highest cumulative proof-of-work or longest hash chain wins.
This is a last-resort conflict resolution; normal operation
should never produce conflicts.

**MESH-R21.** Chat messages from a device that has left the mesh
MUST remain in the log. They MUST be marked with the device's
display_name and departure timestamp.

### 4.6 Security

**MESH-R22.** All mesh communication MUST be encrypted. LAN mode
MAY use TLS with self-signed certificates pinned on first use
(TOFU). WAN mode MUST use TLS with certificate verification
against a known relay certificate.

**MESH-R23.** Device private keys MUST NOT leave the device. They
MUST be stored in the device's local keyring or TPM if available.

**MESH-R24.** A compromised device MUST be revocable. Any device
MAY broadcast a `revoke_device` message signed by its own key,
naming the compromised device. Revocation takes effect when
a majority of active devices have echoed the revocation.

**MESH-R25.** The mesh MUST NOT trust any single device. All
results MUST be locally verifiable. All signatures MUST be
locally verifiable. The mesh is trustless by design.

### 4.7 Observation Integration

**MESH-R26.** All mesh events MUST be observed through the existing
observation layer. Event kinds:

| Event | Kind | Payload |
|---|---|---|
| Device joined | `custom` | device_id, display_name, capabilities |
| Device left | `custom` | device_id, reason |
| Message sent | `custom` | message_id, kind, author_id |
| Task proposed | `custom` | task_id, goal_spec_hash |
| Model offered | `custom` | task_id, device_id, model_name |
| Task assigned | `custom` | task_id, device_id |
| Result broadcast | `custom` | task_id, receipt_hash, outcome |
| Result disputed | `custom` | task_id, dispute_reason |
| Device revoked | `custom` | device_id, revoker_id |

**MESH-R27.** Mesh observations MUST be emitted by every device
for every mesh event it observes, regardless of whether it
participated in the event. This creates redundant, cross-device
observable history.

---

## 5. Implementation Modules

```
residual/
├── mesh/
│   ├── __init__.py
│   ├── identity.py      # MeshIdentity, key management
│   ├── discovery.py     # mDNS LAN discovery, relay connection
│   ├── message.py       # MeshMessage, signing, verification
│   ├── chat.py          # Group chat log, hash chain, conflict resolution
│   ├── tasks.py         # Task proposal, model offer, assignment
│   ├── security.py      # Encryption, revocation, TOFU pinning
│   └── observer.py      # Mesh event → observation layer bridge
```

---

## 6. What This Does NOT Change

| Component | Why Unchanged |
|---|---|
| `engine.py` | Mesh is above the engine; engine runs local tasks |
| `station/service.py` | Station orchestration unchanged; mesh calls station |
| `goalspec.py` | GoalSpec is mesh-agnostic; mesh broadcasts it |
| `verifier.py` | Verifiers are mesh-agnostic; mesh broadcasts results |
| `quarantine.py` | Quarantine is local; mesh tasks enter local quarantine |
| `loop.py` | LoopController is local; mesh tasks run through it |
| Synchronous constraint | Each device is synchronous; mesh is async by nature |

---

## 7. Open Questions

1. **Relay trust model:** Who runs the relay? Self-hosted by one
   device? Third-party service? This affects WAN mode security
   significantly.

2. **Capability scoring:** Self-assessed scores are gameable. A
   device could overstate its capability to win tasks. Reputation
   system needed?

3. **Task partitioning:** For large tasks, can multiple devices
   work on different parts simultaneously? This requires the
   sub-agent pool (SPEC-006) and CRDT merging (Frontier 4).

4. **Offline tolerance:** What happens when a device goes offline
   mid-task? The task needs to be reassignable. Lease expiry
   from the station layer may apply.

5. **Message retention:** How long should the shared chat log be
   retained? All devices forever? Prunable? This affects storage
   on resource-constrained devices.
