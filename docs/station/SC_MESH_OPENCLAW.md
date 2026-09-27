# OpenClaw mesh adapter boundary

SPEC-SC-MESH-001 does not treat an existing OpenClaw chat session as execution authority.

The candidate adapter has two hard requirements before it may advertise bounded execution:

1. OpenClaw must expose the pinned `agent exec` contract used by the adapter.
2. A host-local mesh config must select `tools.profile: minimal`, allow only `session_status`, and explicitly disable elevated execution.
3. The run is launched as a transient systemd unit with `KillMode=control-group`; Windows execution remains unsupported until an equivalent process-tree containment profile is implemented and qualified.
4. The completed JSON envelope must report zero tool calls. A textual completion or transport ACK is never a Station verification receipt.
5. Fallback models are supplied only from the Station-admitted provider plan. Missing provider-attempt evidence remains conservative rather than being synthesized.
6. Gateway-backed `openclaw agent` execution is not used for bounded tasks because transport loss may be ambiguous and the Gateway process is outside the transient execution cgroup. Gateway transport can still be used for communication after its own qualification.

Credentials are not copied into the adapter configuration. Setup must use the host's supported OpenClaw credential mechanism and keep secrets outside exported mesh artifacts.

This file describes implementation boundaries only. It is not evidence that OpenClaw 2026.6.1 on any live host supports `agent exec` or satisfies the systemd containment contract. That remains a W5/W7 qualification gate.
