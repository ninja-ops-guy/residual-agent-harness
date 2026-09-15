# Mission Control — World-Class Demo Acceptance

The public demo is judged as a product surface over the real RESIDUAL Harness, not as a static showcase.

## 10/10 demo criteria

1. **Prompt first.** Chat is the default surface. Advanced execution controls stay secondary.
2. **Real guest execution.** Work runs in the browser Linux guest through the real Harness; no scripted model fallback is permitted in the shipped path.
3. **Conversation continuity.** A follow-up build carries the immediately preceding accepted artifact bundle as frozen evidence with an explicit parent mission ID. `New chat` starts a new lineage; `Fresh artifact` detaches the next build without erasing conversation history.
4. **Evidence-bound revisions.** Parent result, trace, manifest, persisted bytes, hashes, paths, and size limits must all agree before any provider dispatch. Tampered parents fail before inference.
5. **Useful outputs.** Build mode emits bounded downloadable files, not only prose. Browser apps are requested as directly previewable static bundles.
6. **Immediate preview.** Generated HTML is rendered inline and in Files using an opaque-origin `sandbox="allow-scripts"` iframe with network, frames, objects, forms, and external resources blocked.
7. **Runtime proof without overclaiming.** Preview instrumentation reports a bounded startup runtime smoke result. A smoke PASS means the preview loaded without observed startup JavaScript errors; semantic/code correctness remains `UNKNOWN` unless stronger verification exists.
8. **Inspectable background.** Activity, Evidence, Files, and Terminal expose what happened without forcing implementation detail into the normal chat flow.
9. **Persistent demo sessions.** Browser-local conversation state restores recent turns and the latest accepted preview after reload. Guest run files remain the authoritative evidence for each mission.
10. **Claim discipline.** Real provider login/inference, Safari, physical-device behavior, hosted identity, cross-device history, and server-enforced quotas are never claimed unless separately evidenced.

## Authority boundary

Conversation continuity and preview execution do **not** grant generated code repository mutation or M4 authority. Accepted generated files remain under the mission artifact directory. Repository-changing autonomous work still belongs behind Factory/M4 policy, verification, and integration controls.

## Production acceptance

Every release that changes this surface must retain real-browser evidence for desktop and narrow Chromium against the exact deployed revision, covering guest attachment, actual Harness execution, generated files, trace/result verification, isolated preview behavior, and optional-provider isolation before opt-in.
