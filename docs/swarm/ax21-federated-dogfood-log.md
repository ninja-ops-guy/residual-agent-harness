# AX-21 — Federated Swarm Dogfooding Experiment Log

Status: ACTIVE / contemporaneous record  
Date: 2026-09-19  
Authority: research evidence only; this document does not satisfy production qualification gates.

## Objective

Evaluate whether RESIDUAL increases **verified useful work per unit of operator coordination effort** while preserving verification, lease, scope, review, and integration authority across a heterogeneous multi-host agent swarm.

Primary denominator:
- operator active minutes;
- operator intervention count.

Interventions are classified separately (infrastructure, approval/HITL, credentials, recovery, task clarification/reassignment, conflict resolution) so legitimate HITL decisions are not conflated with coordination friction.

The seven-phase dogfooding program governs this campaign. Routine activity is not promoted to a finding. Record material findings, HITL decisions, phase transitions, retained failures, authority violations, and RES-UP candidates.

## P1 — Multi-host enrollment / transport

### B0-3 HITL decision

Decision: **Option A — LEGION SSH-tunnel hub**.

Rationale recorded for the experiment: validate RESIDUAL distributed operation using the documented loopback/SSH transport pattern without introducing an additional overlay-network control plane during P1.

Planned topology:
- RESIDUAL station remains bound to loopback on LEGION/WSL.
- DELL7320 and DBOX establish local SSH forwards to LEGION.
- Only TCP/22 is exposed on the LAN-facing hub.
- Tunnel account is key-only and restricted to forwarding the station endpoint.

### Hub Phase 1 — unprivileged preparation

Reported complete by Ghost.

Tunnel identity:
- account: `residual-tunnel`;
- shell: `/bin/false`;
- password locked;
- key-only authentication;
- no PTY;
- no X11 forwarding;
- no agent forwarding;
- permitted forwarding restricted to `127.0.0.1:8765`.

Reported negative/positive transport evidence:
- intended tunnel -> station root: HTTP 200;
- shell attempt: rejected;
- forwarding to unauthorized target `:11434`: administratively prohibited;
- wrong key: denied;
- station reachable through Windows loopback/WSL forwarding.

These are reported observations from the live swarm session and require preservation of the underlying command/output evidence in the P1 evidence bundle.

### Hub Phase 2 — pending elevated operator action

One elevated Windows pass remains required. Ghost's later host reconnaissance materially revised the topology:

- Windows OpenSSH Server capability is absent before the elevated pass; client tools only.
- Loopback TCP/22 is already occupied by WSL/wslrelay.
- Planned Windows `sshd` binding is therefore loopback `127.0.0.1:2222`.
- LAN chokepoints are two explicit portproxy mappings:
  - `192.168.5.161:22 -> 127.0.0.1:2222`
  - `192.168.99.2:22 -> 127.0.0.1:2222`
- Removing either mapping provides a host-specific remote transport revocation mechanism without changing the station or sshd listener.
- Inbound firewall scope is limited to TCP/22 from the two relevant private network ranges during enrollment, with a recorded intent to tighten after first successful connects.

The staged elevated installer is reported as idempotent: it installs/configures OpenSSH Server, configures the restricted tunnel identity, delete/recreates the two exact portproxy mappings rather than accumulating stale mappings, and checks for the named firewall rule before create/update.

This is an **operator infrastructure intervention** and must be included in the operator-effort denominator.

Acceptance is explicitly verify-don't-trust. Preserve outputs for:
- `netsh interface portproxy show v4tov4`;
- firewall rule state;
- TCP listeners on 22/2222;
- live connection tests to both LAN endpoints;
- SSH host-key fingerprints.

Successful installer exit alone is not P1 evidence.

### DELL7320 / Wrench enrollment state

Reported:
- tunnel key generated;
- only public key shared with hub coordinator;
- target hub endpoint staged;
- Ollama available;
- model: `qwen2.5-coder:7b`;
- worker held until hub elevation completes.

### DBOX / Scout B0-9 capability manifest

Reported manifest:
- OS: Linux Mint 22.3, kernel 6.17.0-35-generic;
- CPU: Intel Core i5-7500T @ 2.70 GHz, 4 cores;
- RAM: 16 GB total, ~13.1 GiB available at observation;
- GPU: Intel HD Graphics 630; CPU inference;
- disk: Samsung 860 EVO 500 GB SATA SSD, ~403 GB free;
- network: 192.168.1.6/24 plus direct-link 192.168.99.1/24 segment;
- Ollama: installed user-space during enrollment, reported v0.34.2;
- model: `qwen2.5-coder:7b`;
- native and OpenAI-compatible local chat paths reported verified;
- cold first load reported ~10 s; short reply evaluation ~2.7 s;
- Ollama is a user process and will require restart after reboot.

Preserve this manifest because P2+ will operate on heterogeneous hardware and later assignment/throughput analysis should condition results on node capability.

### B0-6

Status: CLOSED / ACCEPTED by KimiConductor.

Reported station-side retained lifecycle evidence:

- project `p-76cd46aacb98`: remote STAR claimed OPS-101 and remote Mason claimed OPS-102 at ~15:32:37, attempt 1; both leases later expired and tasks transitioned to blocked with owners cleared; after operator triage/requeue, Mason reclaimed at attempt 2 and produced `usage.recorded` before reaching review-ready.
- project `p-d4dd2d7b4e21`: Hammer/Hermes claimed work at ~15:33:03; expiry was recorded later; after requeue Hammer completed an attempt-2 loop with `usage.recorded` and reached review-ready.
- heartbeats are not retained as project events; they operate through the lease path. The retained record is therefore claim/expiry/transition/submission/usage evidence rather than heartbeat events.

The B0-6 negative-test battery is retained as the enrollment fail-closed suite. Do not overwrite first-failure or race evidence with later clean reruns.

### Material finding AX21-F002 — expired work requires operator triage before reclaim

Organic enrollment observation: lease expiry transitions affected tasks to `blocked`, clears ownership, and does not automatically return the task to reclaimable/ready state. Operator triage was required before the second attempt could be claimed.

Current classification: **scheduler/recovery friction finding**, not automatically a defect. Fail-closed blocking after authority expiry is safety-preserving; the experiment must determine whether bounded automatic recovery can reduce operator effort without weakening authority.

### RES-UP candidate AX21-RES-UP-002

**Policy-governed post-expiry recovery**

Evaluate a deterministic recovery policy that distinguishes:
- safe-to-requeue lease expiry with no accepted candidate/effect;
- expiry requiring HITL because evidence/state is ambiguous;
- repeated expiry requiring quarantine/escalation.

Replay acceptance should prove:
1. no stale lease regains authority;
2. no duplicate candidate/integration authority is created;
3. safe cases can return to reclaimable state without operator triage;
4. ambiguous cases remain BLOCKED/HITL;
5. recovery decisions are retained as evidence;
6. operator interventions are compared against the organic B0-6 baseline.

## Material finding AX21-F001 — stale buffered instruction execution

Observed at least twice during live swarm coordination.

Latest observation:
- Mason/LEGION began executing B0-6 after B0-6 had already been CLOSED/ACCEPTED.
- KimiConductor intervened and stopped execution before the stale work proceeded materially.
- Coordinator explicitly identified buffered instructions as the source of stale execution intent.

Interpretation/hypothesis:
A delivered/buffered instruction can outlive the authoritative task state. Human/coordinator awareness currently prevents some stale execution, but the transport/message itself is not sufficient authority to act.

This is a dogfooding finding, not yet a proven core-runtime defect.

### RES-UP candidate AX21-RES-UP-001

**Generation/state-bound dispatch precondition**

Candidate invariant:

> Buffered message != current authority.

Every executable agent instruction should be bound to authoritative state, for example:

`mission_id + task_id + task_generation + expected_state + authority_epoch/lease`

Immediately before tool execution or task start, compare the instruction binding with current authoritative state. If the task has advanced, closed, been superseded, or authority moved, classify the instruction as STALE and refuse execution.

Required replay experiment:
1. create valid instruction at generation N / expected RUNNING;
2. advance authoritative task to ACCEPTED/CLOSED or generation N+1;
3. deliver/replay buffered N instruction;
4. verify zero tool execution and zero candidate mutation;
5. record deterministic STALE disposition;
6. compare operator intervention requirement with the two organic observations.

Success target: stale-command operator interventions fall to zero for covered cases.

## P1 exit criteria

Do not declare P1 complete until all are evidenced:
1. LEGION, DELL7320, and DBOX are enrolled simultaneously;
2. runner-to-manifest identity binding is recorded;
3. remote tunnel transport is demonstrated independently;
4. tunnel interruption/reconnect is demonstrated;
5. stale/duplicate lease behavior remains fail-closed;
6. B0-6 retained evidence is included;
7. worker credential is rotated after all three enroll;
8. pre-rotation credential is demonstrated invalid and never retained as fallback;
9. all workers reconnect successfully with the replacement credential;
10. operator-effort ledger is frozen for P1.

Presence/roster screenshots may support operational context but are not identity or authority evidence.

## Operator-effort ledger

KimiConductor reports the ledger is live and was backfilled with **8 operator interventions** from the day's activity spanning infrastructure, approvals, credentials, and recovery.

This count is currently a reported datum. The final evidence bundle should contain event-level entries with timestamps/category and active minutes rather than relying only on the aggregate.

Derived metrics to compute after each phase:
- verified accepted outputs / operator interventions;
- verified accepted outputs / operator active minute;
- verified accepted tasks / total attempts;
- verifier reject/repair rate;
- recovery interventions / injected or organic faults.

## P2 — queued distributed mission

Mission: **RES-UP case-study production**.

Reason for selection:
- real backlog;
- naturally separable work;
- no autonomous upstream write authority required;
- exercises the evidence pipeline end-to-end.

Planned four-role split:
1. research/evidence;
2. implementation/drafting;
3. verification/challenge;
4. integration analysis.

P2 begins only after P1 exit is demonstrated.

The experiment should allow the swarm to perform its own bounded decomposition where safe. Human instructions that specify coordination mechanics beyond genuine authority/HITL requirements must be logged as operator interventions.

## Evidence handling rules

- Preserve first failures.
- Negative results remain results.
- Do not reinterpret UNKNOWN/SKIPPED as PASS.
- Keep worker-reported usage distinct from provider-authoritative usage.
- Preserve exact mission/task/lease/revision identifiers where available.
- Preserve capability manifests alongside performance measurements.
- Separate operational presence from durable evidence.
- Separate research evidence from production qualification.
- Record organic failures before remediation so replay experiments can test whether RES-UP changes reduce operator effort.

## Next evidence checkpoint

The next material checkpoint is either:

**P1 PASS** — frozen evidence IDs/hashes + operator-effort totals + P2 transition,

or

**P1 BLOCKED/FAIL** — first unresolved invariant and exact HITL action required.
