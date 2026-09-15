# Mission Control — World-Class Demo Acceptance

The public demo is judged as a product surface over the real RESIDUAL Harness, not as a static showcase.

## 10/10 demo criteria

1. **Prompt first.** Chat is the default surface. Advanced execution controls stay secondary. Sending a remote mission while disconnected opens provider setup without clearing or submitting the prompt; provider connectivity alone is not per-prompt consent.
2. **Real guest execution.** Work runs in the browser Linux guest through the real Harness; no scripted model fallback is permitted in the shipped path.
3. **Truthful terminal states.** `Build completed` is shown only when the trace-bound result is successful and contains an accepted, non-empty generated-file bundle. Provider/transport/protocol/verifier failures are `BLOCKED`/`INCOMPLETE`, produce no preview, and never advance artifact lineage.
4. **Conversation continuity.** A follow-up build carries the immediately preceding accepted artifact bundle as frozen evidence with an explicit parent mission ID. `New chat` starts a new lineage; `Fresh artifact` detaches the next build without erasing conversation history.
5. **Evidence-bound revisions and sessions.** Every build commits its conversation identity in the Harness run-start artifact hashes. Parent result, trace, manifest, persisted bytes, hashes, paths, session identity, and size limits must all agree before provider dispatch. Parent mission ID and trace root are frozen into the child `prior-lineage` evidence. Revision depth is reconstructed recursively from verified lineage, not mutable summary/UI metadata. Cross-session grafts and tampered parents fail before inference.
6. **Useful outputs and immediate preview.** Build mode emits bounded downloadable files, not only prose. Browser apps are requested as directly previewable static bundles and render inline using an opaque-origin `sandbox="allow-scripts"` iframe with network, frames, objects, forms, and external resources blocked.
7. **Runtime proof without overclaiming.** Preview instrumentation reports a bounded startup runtime smoke result. A smoke PASS means the preview loaded without observed startup JavaScript errors; semantic/code correctness remains `UNKNOWN` unless stronger verification exists.
8. **Engineer explainability.** Activity includes a human-readable projection of the actual guest/Harness stages: what happened, why the state changed, and the next useful action. This explanation is not a new trust anchor; Evidence/Terminal retain the authoritative trace, receipts, result binding, and raw event details.
9. **Persistent demo sessions.** Browser-local conversation state restores recent turns and the latest accepted preview after reload. Browser storage is convenience state only; guest run files and verified trace-bound artifacts remain authoritative for mission and lineage evidence.
10. **Claim discipline and safe failures.** Real provider errors cross the browser bridge only as a bounded safe code vocabulary; raw upstream exception bodies/credentials are not written into evidence. Real provider login/inference, Safari, physical-device behavior, hosted identity, cross-device history, and server-enforced quotas are never claimed unless separately evidenced.

## Authority boundary

Conversation continuity, engineer-facing explanations, and preview execution do **not** grant generated code repository mutation or M4 authority. Accepted generated files remain under the mission artifact directory. Repository-changing autonomous work still belongs behind Factory/M4 policy, verification, and integration controls.

## Production acceptance

Every release that changes this surface must retain real-browser evidence for desktop and narrow Chromium against the exact deployed revision, covering guest attachment, actual Harness execution, generated files, trace/result verification, isolated preview behavior, multi-turn parent lineage, session isolation, reload restoration, and optional-provider isolation before opt-in.

The browser proof must also execute the negative provider path: Send while disconnected must preserve the unsent prompt and open provider setup; a connected-but-unconsented prompt must remain unsent; a provider failure must end `BLOCKED` with no generated preview/artifact and with an engineer-readable stage/WHY/NEXT explanation. Synthetic provider fixtures prove the transport/UI contract only; a real user/provider run remains separate interoperability evidence.
