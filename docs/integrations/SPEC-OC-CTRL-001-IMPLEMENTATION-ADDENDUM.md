# SPEC-OC-CTRL-001 — implementation addendum R1

**Priority: owner-selected P1 / v1. Status: SOFTWARE CANDIDATE; RELEASE HOLD.**

This addendum preserves the original ten v1 gates. It records what the 0.2.0 software candidate actually supplies and the work still needed. The preceding 0.1.0/addition-only description is superseded for the current #501 generation; no release gate is promoted by this documentation correction. It does not replace unresolved requirements with weaker fixture success.

## Source and integration boundary

Inspected accepted main: HEAD `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`, TREE `7cd0d32be6fd61948f2fce753b122e5b6f0c6500`. The current #501 software predecessor is HEAD `eebf3f0c0e2877531076e8ebc3123ecb4e2abb19`; package metadata is version `0.2.0`. Unlike the earlier 0.1.0 generation, the current candidate is not addition-only: it changes `integrations/openclaw-control` and adds bounded Station-side remote-worker contracts/service/server integration plus Station regressions. It does not modify accepted `main`; the changes remain unmerged candidate bytes. It does not edit the kernel, mesh, provider-continuity implementation, release checklist, or required-check policy.

Existing OpenClaw/mesh/continuity work is distributed across separate candidates, including #10, #340, #400, #404, #489 and #493. No implementation from these branches is silently imported. #495's single-Station plan remains an integration plan rather than release evidence. The current candidate now contains a Station remote-worker bridge and regression coverage, but that software path is not native/live qualification and does not by itself establish Station acceptance. Accepted main's `residual/engines/protocol.py` remains the runtime-neutral execution boundary; OpenClaw-specific authority must not move into the kernel.

## Corrections to the original design

1. An in-process plugin cannot supervise its own death and independently prove process replacement. A trusted external, narrowly scoped supervisor must implement restart/cancel and independent lifecycle observation. PID alone is insufficient; bind boot identity, start evidence, gateway identity and exact configuration/source tuple.
2. Cryptographic digest equality is byte integrity, not sender authenticity, truthful evidence or authority. Signed external commands and gateway transport authentication are separate from runtime-reported event digests. All local events retain `RUNTIME_REPORTED` and `NOT_EVALUATED` acceptance.
3. Qualification is not a single state ladder ending in authority. Enrollment, capabilities, configuration, provider observations, qualification receipts, command authorization, native execution, verification and Station acceptance are independent dimensions.
4. Supported hooks are exact-version contracts. This package uses the source-inspected native `before_agent_run` block/pass contract and `before_tool_call` block contract. A test double cannot establish that a real host invokes or enforces either hook on every relevant path.
5. Native session completion, a successful nonce response, a command timeout, and revocation each have narrower semantics than accepted work, qualified providers, terminated execution or completed cancellation.

## Required remaining implementation lanes

| Lane | Concrete deliverable | Exit condition |
|---|---|---|
| OC-NATIVE | Load exact package on one dedicated exact-build OpenClaw canary; exercise normal and bypass entry paths; prove event/session/run correlation and config reload behavior. | Native loader/auth/hook enforcement receipt with source bytes and failure controls. |
| OC-STATION | Current 0.2.0 candidate includes a bounded Station remote-worker bridge that binds remote evidence to project/task/attempt/operation and Station packet/response digests while leaving remote evidence non-authoritative. Complete any remaining controller authority/adapter wiring through existing Station admission, budget/deadline and verification boundaries. | A real Station parent dispatch produces a result through the native plugin and existing independent verification alone determines acceptance; fixture/software PASS is insufficient. |
| OC-LIFECYCLE | External allowlisted gateway supervisor; authenticated native cancellation; old/new process and listener/config identity proof; durable post-restart reconciliation. | Verified stop/cancel and restart postconditions; no in-process self-attestation, arbitrary shell or ambiguous replay. |
| OC-LIVE | Owner-authorized provider/model canary using existing credential custody, real readiness, meaningful task, negative provider case, drift/disconnect/revocation cases. | Exact-tuple live receipts, retained first failure and restoration proof. |
| OC-RELEASE | Independent review and clean reproduction; combine only explicitly selected candidates; rerun changed integration/full release gates on exact final tree. | All original gates PASS, exact-head maintainer acceptance and truthful release claim. |

These lanes are **not dispatched to the live swarm by this document**. Native/live gates need access to an authorized canary and externally produced evidence. No production config, provider credential, agent state, budget or service is mutated by writing this candidate.

## Qualification campaign and oracle

Preregister one exact runtime/build/plugin/config/controller-key-ID tuple and a new campaign ID. Capture the existing process/listener and non-secret configuration identity externally. Do not place private controller keys in the gateway's security principal. Stage default observe-only and prove unauthorized access causes zero model/tool invocations. Only then enable the bounded candidate profile under fresh explicit authority.

Run OC-V1-01 through OC-V1-10 with a known expected output and a deliberately unsatisfied acceptance condition. Independently measure native calls, outputs and side effects; the plugin's own PASS labels are not the oracle. Use an actual provider for live qualification. Stop at the first failing gate, preserve its bytes and outcome, and create a successor generation after a fix. No assertion weakening, retry-until-green, key publication or result reconstruction from chat.

In particular, cancel must prove execution cessation rather than merely revoked acceptance. Restart must be requested and verified outside the dying gateway. Loss of the controller must deny fresh dispatch before any new provider I/O; previously admitted work follows its bounded authority. Reconnection requires identity/config/source and durable-ledger reconciliation, not automatic restoration of stale authority.

## Publication and release policy

The software qualifier records exact source-file SHA-256 values before and after execution, raw logs and local environment. A local source-set digest is not a repository tree hash. A hosted PR workflow may run on a synthetic merge commit; record and distinguish that SHA from the source PR head. Fixture PASS is not native PASS; native PASS is not provider-live PASS; component PASS is not integration PASS.

This feature remains P1 and **not release-admissible** until all ten gates, native cancel, existing Station acceptance and independent exact-tree qualification are complete. Native UI, native SC-MESH, sophisticated failover, fleet management and self-hosting remain successors and must not expand the bounded v1 release surface automatically.

Permitted current claim: “A tested software candidate implements signed, durable, text-only OpenClaw control primitives with an external controller client and a bounded Station remote-worker bridge; native/live release qualification remains incomplete.” Prohibited current claim: “RESIDUAL v1 has a qualified OpenClaw control plane.”
