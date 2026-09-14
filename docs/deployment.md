# Deployment integration guide

This is an opt-in integration layer, stacked on the v0.5 gap-closure work. It is not a declaration that every original specification is closed or that a production deployment has been certified.

## Install a candidate build

From a checked-out revision, install the components you actually need:

```bash
python -m pip install '.[mesh,hitl,marketplace]'
python -m pip wheel . --no-deps -w dist
python -m examples.deployment.lifecycle
```

The base wheel includes `residual`, `ai_providers`, and `observation_layer`. Do **not** install an unrelated package named `observation_layer` to work around an import failure. Verify which wheel and interpreter you are running. Optional extras install the WebSocket, cryptography, multicast, HTTP, and JWT libraries. Core imports do not require these extras.

The candidate wheel retains version 0.5.0; use the commit recorded in the CI evidence artifact to identify this build. No PyPI publication is implied.

## Wire a station without replacing its existing modules

`residual.station.deployment.deployment_extensions(hitl_gateway=..., tui=True)` returns a factory for `Station(root, extension_factory=factory)`. It preserves the default SecOps, mission, trajectory, and successful-memory modules, then adds the host-supplied HITL gateway and a per-project terminal observer. The extension registry still freezes in the controller constructor. Network services must be started explicitly by the host.

The terminal observes the actual extension event stream and renders in a separate thread. Stop/detach it when the run closes. Do not share one mutable collector across concurrent projects. TUI failure does not authorize or veto a run.

`python -m examples.deployment.lifecycle` is an executable, credential-free example of `EngineHarnessPass`, ordered verification, automatic trajectory recording, SUCCESS-only memory indexing, a live-reverified memory context, and explicit golden promotion. It is a deterministic fixture, not a model benchmark.

### Memory and golden trajectories

`MemoryContextAssembler` accepts only host-declared `MemoryRequest` objects. Each request includes the expected current verifier revision and a callback that validates the active task, evidence, parents, and candidate. Hash integrity alone does not authorize reuse. Missing, corrupted, rejected, or revision-mismatched entries are omitted. A byte cap bounds the assembled context. The host must separately enforce whether any retrieved content may be sent to a remote engine.

`GoldenTrajectoryStore` stores named references to intact, successful trajectories. `promote(name, hash)` creates a reference; replacing one requires `expected=old_hash`. There is no automatic golden promotion. `compare(name, trajectory)` uses the existing structural regression engine; it does not compare private reasoning or raw model output.

The binding Conflict 3 takes precedence: exceptions and unavailable evaluators produce `UNKNOWN`. UNKNOWN never passes, and later judge checks skip. A malformed evaluator return remains a contract failure. Unexpected execution exceptions close the lifecycle as ABORTED exactly once, then propagate the original host exception. An exception is not silently converted to successful execution.

## Authenticated operator review

The new authenticator verifies JWT access tokens issued by your configured identity provider. It is a **resource-server adapter**, not a browser OAuth authorization-code/PKCE login flow, LDAP client, SAML service provider, or universal SSO integration.

Provision a dedicated audience and `residual:review` scope at the issuer. Map a flat role claim to explicitly allowed roles such as `operator`. Use short-lived access tokens. The adapter requires issuer, audience, subject, issue time, expiry, scope, role membership and a pinned signing key. It permits RS256/RSA (at least 2048 bits) or ES256/P-256 only. Token-supplied key URLs and embedded keys are rejected.

Obtain the issuer's **public JWKS through your trusted deployment process**, validate its provenance, and mount it as a local JSON file. No keys are fetched during approval or inside a database transaction. Pinned keys expire after one hour by default; reload/restart with the current JWKS before expiry and after key revocation/rotation. Unknown or stale keys fail closed. A production OIDC client login flow and automatic key-refresh service remain deployment work.

Generate a random HMAC key of at least 32 bytes in your secret manager. Supply its base64 encoding as `RESIDUAL_HITL_SIGNING_KEY` to both the execution host and review service. They must use the same challenge directory and key. Never put this key in a repository, token URL, or command-line argument. Protect the directory, database and key with OS permissions. HMAC-key rotation requires a deliberate challenge migration/invalidation plan.

Launch the optional service using your actual issuer and certificate paths:

```bash
residual-hitl --data /srv/residual/challenges \
  --issuer https://identity.example.test/tenant --audience residual-review \
  --jwks /etc/residual/issuer-jwks.json --role operator \
  --host 0.0.0.0 --port 8766 --origin https://review.example.test:8766 \
  --tls-cert /etc/residual/tls/cert.pem --tls-key /etc/residual/tls/key.pem
```

The example issuer/domain and files must be replaced by operator-owned configuration. Non-loopback listeners require TLS. The fixed origin and Host checks are intentional; configure the correct external authority instead of weakening them. Authenticate all reads and writes. If a reverse proxy is used, preserve the configured Host and terminate/re-encrypt TLS according to your deployment policy; arbitrary forwarded headers are not trusted.

The UI accepts a short-lived review access token, keeps it in memory only, renders untrusted action text literally, and supports explicit approve/deny decisions. Clear the credential after review. Bearer tokens are not written to localStorage, sessionStorage, audit records, or access logs. Protect the endpoint with organizational rate limits and monitor resource usage before exposing it widely.

A decision is bound to the challenge ID, server signature, action, goal-spec hash, role and requested decision. The gateway validates the identity again, atomically consumes a pending challenge, and signs a resolution containing subject, issuer, role, decision and time. Replays and expired challenges are rejected. Denials are durable. On request timeout, re-read challenge status: a database decision may have completed even if the client disconnected.

**Approval never resumes execution, amends the goal, overrides quarantine, or proves that the action was applied.** A trusted operator/host must start an explicitly authorized next run through the existing control plane.

## Mesh transport and discovery

The `MeshNode` message model now has optional real transport rather than only in-process passing:

| Component | Responsibility |
|---|---|
| `DeviceKeys` / `PeerKeys` | Ed25519 signing and X25519 encryption identities; host-provisioned keys |
| `EnvelopeCodec` | Bounded, versioned signed AES-GCM ciphertext envelopes, scoped to room and recipient |
| `WebSocketMeshTransport` | Async direct TLS WebSockets or a relay connection, bounded queues and connection limits |
| `OpaqueMeshRelay` | Routes ciphertext to explicitly provisioned online devices; no payload decryption key |
| `MDNSDiscovery` | Publishes bounded identity/fingerprint/capability metadata and reports advisory LAN candidates |

The host must persist private keys securely, pin both peer public keys out of band, and explicitly call `MeshNode.connect_peer`. `EnvelopeCodec` checks the pinned signing identity against the admitted peer. A discovery advertisement does not authenticate a device and never admits a key, starts a model, dispatches a task, or imports code. Keyring/TPM storage and automated enrollment are not implemented.

Direct clients use `wss://` and verify certificates and hostnames. Pass a dedicated CA trust context for a private PKI. The plaintext option exists only for explicit loopback testing; it is rejected for other hosts. Inbound peers must send an authenticated envelope promptly. Device-signed messages are still independently verified by `MeshNode.receive_message`. Accepted task-result messages remain candidate evidence, not permission to execute or proof of a correct receipt.

The relay requires a distinct random bearer credential of at least 32 characters per device, in an Authorization header, never a query string. Store a JSON mapping of device IDs to credentials in an owner-only file (0600 on POSIX). To launch it:

```bash
residual-mesh-relay --credentials /etc/residual/relay-peers.json \
  --tls-cert /etc/residual/tls/cert.pem --tls-key /etc/residual/tls/key.pem \
  --host 0.0.0.0 --port 8767
```

Clients connect to `wss://relay-host:8767/mesh/device-id`. The relay authenticates that identity and permits one active connection per device. It can see routing metadata and can drop or reorder traffic, but payload confidentiality and signatures are end-to-end. No claim of forward secrecy is made for the static recipient encryption key.

For LAN discovery, construct `MDNSDiscovery(identity, address=explicit_lan_ip, port=listener_port, on_candidate=host_review_callback)`, then await `start()` on the owning event loop. Stop it with `close()`. Only private/link-local/loopback interface addresses are allowed. Interface/firewall/multicast behavior needs validation on your actual network; a loopback multicast CI test is not a physical cross-device LAN test.

### Important mesh limitations

The inherited chat is a **single-head ordered hash chain**. Concurrent independent histories diverge and are rejected; this integration does not pretend to solve consensus or merge divergent logs. Use an explicitly ordered session for the initial rollout. An offline recipient is an error, not successful delivery. There is no durable relay queue, automatic reconnect/catch-up, cross-restart replay database, quorum revocation, or exactly-once application acknowledgement. `send()` means wire submission only. Received messages are placed in a bounded queue for host handling; no remote command or tool-execution RPC is exposed.

Use run-scoped services on their owning event loop, explicitly bind any abort coordinator to that loop, and await shutdown. The existing coordinator's fallback-thread behavior is not a general cross-event-loop cancellation guarantee. These components are not a process sandbox or a proof that arbitrary third-party async code stops within five seconds.

## Live-model validation and cache measurement

Install and provision the requested model yourself; this command never downloads a model, starts Ollama, contacts a cloud fallback, or substitutes a mock:

```bash
residual-live-benchmark --model llama3.3 --repeats 3 --concurrency 1 \
  --output runs/llama33-cache.json
residual-live-benchmark --model llama3.3 --repeats 3 --concurrency 4 \
  --output runs/llama33-load.json
```

Use a machine with adequate resources for your selected model. The benchmark requires a loopback Ollama endpoint, resolves an installed model name/digest, verifies response model identity, and checks that the model digest did not change during the experiment. Each concurrent trial owns its own provider, verifier registry, harness and SQLite cache.

A seed run fills a receipt-bound cache. Alternating cached/uncached repetitions measure a public synthetic two-obligation DAG with no deterministic solver bypass. Every candidate, including cache hits, goes through the current host verifier. The changed-evidence control must invalidate both obligations, including the dependent receipt. Success, exact value equivalence, receipt DAG integrity, zero-call cache hits, and provider-reported input/output token counts gate any savings calculation.

Results include raw samples, p50/p95 latency, call counts, token counts, model identity, concurrency, limits, and configuration hash. Cache-fill and invalidation samples are retained separately from repeat-task savings. This is repeat-work avoidance, **not** a claim that arbitrary new tasks use fewer thinking tokens. The runtime is not deliberately unloaded between samples, so uncached latency is not cold-model-start latency. SQLite/page-cache warming and GPU scheduling may affect latency. The small fixture is not a representative workload or a statistically conclusive production benchmark.

If Ollama/model access is absent, the command exits 3 and writes `status=blocked`, `live_model_validated=false`, and `token_savings=null`. Simulation-based unit tests validate measurement plumbing only; they cannot produce a live savings result.

## Validation and rollout gates

CI installs the optional dependencies and retains exact source, dependency versions, unit/network/multicast output, a candidate wheel and operator-UI browser evidence. The browser uses a locally signed fixture JWT, not a deployed enterprise issuer. Core CI remains dependency-free and skips optional integration tests when their extras are absent.

Before production: review the stacked PRs, require CI on the exact head, exercise an actual issuer/role/rotation/revocation configuration, test transport and discovery between separate physical devices, define recovery for interrupted/divergent sessions, run the live benchmark on your hardware, and validate monitoring/rate limits/backup/restore. None of these operational checks can be replaced by a green mock test.
