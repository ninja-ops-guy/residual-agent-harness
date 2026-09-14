# Follow-up to the v0.4.0 integration assessment

Base: PR #5 at `fec1facd03a17a6a2a09444ae700ccbd679d91ea`.
This follow-up is stacked separately so transport/auth deployment changes do not overwrite the original engine/marketplace work.

| Assessment item | Source-grounded resolution |
|---|---|
| Mesh has no wire transport | Added signed end-to-end encrypted envelopes, direct TLS WebSockets, an opaque relay and explicit mDNS candidate discovery. No consensus, reconnect/catch-up or durable replay guarantee. |
| HITL has no deployment authenticator/UI | Added pinned-JWKS JWT verification, authenticated async review UI/API, durable approve/deny and resolution identity. A real issuer deployment and browser SSO login flow remain unvalidated/unimplemented respectively. |
| observation_layer missing dependency | Not a current packaging gap: it is in the source tree and wheel package-discovery include list. A clean-wheel import/asset smoke guards this; no unrelated external dependency was added. |
| No real-model evidence | Added an opt-in Ollama model/digest-bound receipt-cache and concurrency benchmark. No live inference or savings claim is made without a successful live run. |
| TUI not wired | Existing collector hooks were present. Added explicit station terminal opt-in using that actual event stream and tested separate rendering-thread lifecycle/detach. |
| Trajectory not wired | Existing station and PR #5 hooks were present. Added exception-close regression coverage and explicit named golden management with integrity checks and compare-and-swap promotion. |
| Memory not wired/retrieved | Existing SUCCESS-only station/PR #5 indexing was present. Added host-selected, revision-checked, actively reverified and byte-bounded context retrieval plus integration tests. |
| Evaluator exception -> FAIL | Corrected to UNKNOWN per uploaded binding Conflict 3; missing evaluators also UNKNOWN. Invalid return contracts still fail closed. |
| compute_cache_key compatibility | Added a static delegate; standalone cache_key remains the canonical implementation. |
| extensions receipt imports | Re-exported StationReceipt, ReceiptReference and cache_key without duplicating implementation. |

Additional correctness work: detach nested lifecycle payloads per subscriber; emit terminal abort lifecycle once on execution exceptions; keep public observations JSON-safe; sign HITL resolution metadata; persist expiry on read; keep bearer credentials out of logs, query strings and browser persistence; default to certificate-verified TLS.

See [deployment guide](../deployment.md) for executable commands, setup requirements, validation boundaries and rollout gates. The original PR #5 adapter, async-coordinator and marketplace claims need their own review; this follow-up does not certify the entire platform as production-ready.
