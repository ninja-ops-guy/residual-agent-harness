# Agentic Mesh & Group Chat Onboarding Qualification

Status: TEST/REVIEW TRACK

## Scope

RESIDUAL currently has two related but distinct communication surfaces:

1. **Agentic cluster + mesh**
   - `residual.cluster` handles authenticated node join, capability exchange, task routing, heartbeats and reassignment.
   - `residual.mesh` holds a signed, hash-chained message history and task/result messages.
2. **Command Station Shared Comms**
   - The Station UI displays the mission's append-only event log and lets the operator post notes.
   - It is not currently a network client for `residual.mesh`.

This distinction is intentional in this qualification. A green Shared Comms browser test does not prove multi-device mesh UI onboarding.

## Review findings

### F1 — Join status was optimistic

Before this review, `ClusterNode.join()` reported `joined=True` after a transport send even when the receiver rejected the JOIN (for example, a wrong cluster key). Onboarding status therefore could disagree with authenticated membership.

Qualification rule: an explicit/discovered peer join is successful only after a valid JOIN_ACK has negotiated a common schema version. A first node with no peers may form a standalone cluster.

### F2 — Late joiners had no history catch-up primitive

A mesh message is chained to the sender's current chat head. A fresh peer starts at `GENESIS`, so it cannot accept a live message after history already exists.

The test track adds `MeshNode.sync_history()` with these rules:

- local history must be an exact prefix;
- every newly appended history message must have an admitted author;
- every signature is verified;
- revoked authors are rejected;
- chain order is enforced by `MeshChat.append()`;
- replaying an identical prefix is idempotent;
- forks are not silently selected or truncated.

This does not define consensus/finality for divergent histories.

### F3 — CHAT could carry structured payload

The mesh spec treats human chat as inert text and structured actions as typed non-chat messages. The prototype previously allowed a CHAT message to carry arbitrary structured payload.

Qualification rule: `MeshMessageKind.CHAT` rejects non-empty payloads. Chat text never becomes an execution channel by itself.

### F4 — Shared Comms is not mesh transport

The Station UI correctly describes Shared Comms as a shared event log with scoped agent delivery. There are no `/api/mesh/` endpoints on this branch. Tests pin this truthfulness so future UI changes cannot imply multi-device chat before the bridge exists.

## Onboarding test matrix

### Cluster admission

- standalone first-node formation;
- explicit unreachable bootstrap fails onboarding;
- wrong-key bootstrap fails onboarding;
- JOIN_ACK/schema negotiation required;
- capability exchange visible immediately;
- third node receives the bootstrap node's current roster;
- leave/rejoin restores membership;
- newly joined capable node can receive a task immediately.

### Mesh chat

- late join cannot accept a live chained message without history;
- verified history catch-up enables live delivery;
- identical history replay is idempotent;
- conflicting prefix fails closed;
- unknown author fails closed;
- invalid signature fails closed;
- out-of-order history fails closed;
- public-key replacement requires explicit re-admission;
- revoked peer cannot rejoin or send;
- CHAT structured payload is rejected;
- message payloads are deeply frozen;
- size limits are enforced;
- three-member history replay followed by live conversation converges to the same head.

### Command Station / browser

- fresh Station boots with no popup;
- setup checklist remains in-page and exposes all four onboarding steps;
- training mission can be launched from the setup checklist;
- training reaches integrated state;
- Shared Comms identifies itself as the event log;
- first operator note is visibly acknowledged;
- HTML/script-like note content is rendered inert;
- operator note survives page reload;
- no unexpected browser console/page errors.

## Non-claims / remaining work

This test track does **not** prove:

- WAN relay encryption or group re-keying;
- production mDNS behavior on physical LANs;
- authenticated membership epochs/quorum;
- divergent-history consensus or finality;
- Station UI ↔ `residual.mesh` transport integration;
- local semantic verification of remote task results beyond the existing cluster/receipt boundaries.

Those require separate design and integration work. The older MESH longest-chain/majority language must not be treated as qualified production consensus semantics.
