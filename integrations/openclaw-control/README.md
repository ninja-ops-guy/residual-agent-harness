# RESIDUAL OpenClaw Control — 0.2.0 candidate

**P1 v1 target; software-component candidate, NOT v1-qualified.** This candidate implements a native OpenClaw plugin, an external signing client, lifecycle-contract helpers, and a bounded Station remote-worker bridge. It remains unmerged and does not change accepted main, existing agents, credentials, or release rules. The Station-side candidate code does not make OpenClaw evidence authoritative or release-qualified. Do not deploy to an existing seat merely because package or Station fixture tests pass.

## What is implemented

A gateway-authenticated, loopback-only plugin route exposes runtime/config observations and Ed25519-signed commands. The managed text-only agent requires a one-use native admission ticket. All its tool calls are denied, including on missing identity. Typed native model/output hooks correlate results to the dispatched session and run. The external controller retains the signing private key; the plugin stores public keys only.

A SQLite WAL/FULL journal persists command intent and evidence in the same transaction before native I/O. Command identity conflicts, expiry, instance mismatch, config drift, clock rollback, missing control lease and unknown capabilities fail closed. Identical active-generation requests are deduplicated. Restart invalidates the in-memory lease and fences the previous instance. Interrupted calls become INDETERMINATE, never automatically replayed. There is no provider-side exactly-once guarantee.

Commands:

- Read: `runtime.inspect`, `config.inspect`, `evidence.read`, `dispatch.inspect`, `dispatch.result`.
- Explicit control: `lease.renew`, `dispatch.submit`, `provider.probe`, `dispatch.revoke`.

Every mutation is individually signed and bound to runtime, boot instance, config digest, action, exact body, operation ID and a maximum 30-second validity window. Renewals are explicit calls, not an autonomous heartbeat. Previously admitted work may finish under its original deadline after a connection loss; no fresh work is admitted without a current lease.

## Run the software tests

Node 22.16 or later is required by this package. Node's built-in `node:sqlite` is experimental in the locally tested Node release. No npm dependencies or model credentials are required.

```sh
cd integrations/openclaw-control
npm test
node qualify.mjs --output /absolute/path/to/new-evidence-directory
npm pack --ignore-scripts
```

`qualify.mjs` writes exact input hashes, syntax checks, test counts, a raw TAP log and a receipt. Existing output directories are refused so earlier evidence is not overwritten. `--require-release` returns exit **3** even after software tests pass: native/live/restart/cancel/independent-review gates remain incomplete, and the Station software bridge still requires a real native end-to-end Station dispatch plus existing independent acceptance. Exit 0 without that flag means software component only. A CI receipt covers its checked-out bytes, not automatically a PR head or a later merge tree.

## Native configuration — stage only

`compatibility.json` records the precise upstream source interfaces inspected at `v2026.6.1`. It is not proof that this version loads or enforces the plugin. Both qualified-version arrays are deliberately empty. `controlEnabled` defaults to false and `hostVersions` must contain an explicitly selected version before candidate control is enabled. A configured version is not qualified support.

Use a dedicated OpenClaw config/state root, a dedicated agent ID and an independently protected controller account. Never reuse a production agent for qualification. Do not install signing private keys into OpenClaw state, environment, workspace or agent-accessible paths. Same-user plugin code is not a security sandbox; a compromised OpenClaw process may falsify its own evidence or bypass its hooks. Independent verification and OS isolation remain required.

Example plugin config (replace the public-key placeholder before loading):

```json
{
  "runtimeId": "oc-canary-01",
  "agentId": "residual-worker",
  "controllerKeys": {"owner": "<Ed25519 PUBLIC key PEM>"},
  "controlEnabled": false,
  "hostVersions": ["2026.6.1"]
}
```

Select the package through OpenClaw's documented native plugin installation mechanism and allowlist only the intended plugin. No install/activation command is executed by this package. The native service places its private journal in `stateDir/residual-control`. POSIX state directory/file mode checks are enforced. Windows ACL qualification is outstanding. State corruption, saturation, or indeterminate executions require operator diagnosis; do not delete the database to replay work.

## External controller

Create Ed25519 keys under a separately protected controller identity. Keep the private PEM file mode 0600 on POSIX. The CLI reads only its path, never a private key or token value from argv. Controller JSON:

```json
{
  "endpoint": "http://127.0.0.1:18789",
  "tokenEnv": "RESIDUAL_OC_GATEWAY_TOKEN",
  "keyId": "owner",
  "privateKeyFile": "/protected/controller/ed25519-private.pem"
}
```

After a separately authorized canary activation:

```sh
node client.mjs inspect /protected/controller/config.json
node client.mjs lease.renew /protected/controller/config.json
node client.mjs dispatch.submit /protected/controller/config.json /protected/controller/task.json
```

Task JSON: `{"provider":"<provider-id>","model":"<model-id>","timeout_ms":1000,"prompt":"<bounded task>"}`. Use an actual registered route; placeholders are not qualification. Poll `dispatch.inspect` with `{"operation_id":"<returned-id>"}`. Only the signed `dispatch.result` surface returns output text. Signed `evidence.read` accepts `{"after":0,"limit":100}` and preserves exact byte envelopes. The client rejects redirects and non-loopback endpoints. It is not a remote-fleet client.

## Important limits

`COMPLETED` is an OpenClaw-correlated result, **not RESIDUAL acceptance**. `provider.probe` validates a random challenge and reported route, **not full provider qualification**. Route claims are runtime evidence, not independent proof of a concealed upstream provider. Config projection is a scoped current-runtime snapshot, not a complete effective provider registry; credential values and rotation are deliberately untracked. Avoid secret-bearing provider URL paths. Generic custom URL path values may appear in the scoped endpoint observation. Prompt/output can contain secrets: ordinary evidence omits prompts, raw errors, tool params and output text, but the private result store and explicitly requested result retain generated content.

The configured agent must exist. Configured fallback arrays are refused in this initial profile. Nonetheless, the full native runtime must independently prove route and hook enforcement: post-result mismatch detection is not pre-invocation policy enforcement. Native model-call counts/cost ceilings are not enforced here. `timeout_ms` bounds result admission and cooperative probe cancellation, not guaranteed termination of a native agent run. `dispatch.revoke` prevents admitting its late result but **does not mean the native process stopped**. Native cancellation and externally verified restart are mandatory unfinished P1 work, not optional claims silently removed from the original spec.

Checksummed local journals detect accidental alteration; a runtime able to rewrite all records and digests can forge them. Controllers must anchor observed evidence tips externally. Persistent-state anti-rollback against a hostile filesystem, secure boot, independent attestation, encrypted result storage, and filesystem ACL isolation are not supplied by this plugin.

Station's existing task admission, project/attempt/generation fences, qualification and independent verification remain authoritative. The 0.2.0 candidate includes Station-side remote execution/evidence validation that binds returned evidence to the Station packet, project/task/attempt/operation identity, and response digest, but that evidence remains non-authoritative until existing Station verification accepts it. The candidate does **not** add a second scheduler or automatically turn plugin evidence into Station acceptance. Native SC-MESH, rolling upgrades, fleet orchestration, fallback continuity and self-building remain outside this candidate. The original P1 gates and remaining lanes are in `docs/integrations/SPEC-OC-CTRL-001-IMPLEMENTATION-ADDENDUM.md` and `OC-CONTROL-P1-GATES.json` in the repository.
