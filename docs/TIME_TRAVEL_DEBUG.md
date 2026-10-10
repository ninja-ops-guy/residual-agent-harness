# Mission Control Time Travel Debugging

Time Travel is a read-only historical inspector for the **browser/WebVM Mission Control** interface. It uses the bounded, privacy-sanitized local diagnostic buffer. It is not the installed Station's separate native Mission Control interface, execution replay, filesystem rollback, or provider re-execution.

## Operation

Open Time Travel and choose a retained run or Full session. First, Last, Step, the keyboard-accessible scrubber, and the event log select a historical event. Jump to failure recognizes failed runs and projected counterexamples; Jump to evidence selects the next evidence event, wrapping when necessary. Unavailable actions are disabled. Refresh history preserves the selected event by ID when retained, otherwise moves to the newest retained event. Inspection does not automatically follow live execution.

The snapshot reconstructs mission status, runtime health, provider lifecycle, projected evidence counts, and release bindings as of the selected event. Run-specific state never carries over from a different run. Global runtime observations may contribute only when already recorded at that time. Missing or evicted information remains unknown. Counts refer to retained projected events, not a claim that the entire authoritative guest ledger is present.

The diff compares adjacent selected snapshots. Event details show sanitized diagnostic JSON. Trace binding identifies recorded run/release/evidence references; it is not an independent integrity attestation. A terminal verified-result projection is not overwritten by subsequent transport completion.

## Appearance and accessibility

The supplied reference guides the green phosphor palette, pixel-art time machine, state/diff panels, event log and timeline controls. The decorative hero is a generated, bundled WebP, with no external image request. Text is rendered as DOM text, not injected HTML. Controls are keyboard accessible, focus survives redraws, and panels stack on narrow screens. The reference's execution Resume and reconstructed-frame claims are not presented as implemented capabilities. Fork Here is explicitly disabled.

## Data and trust boundary

The source is `DemoDiagnostics`, limited to 5,000 in-memory events and approximately 1 MiB of session persistence. Its existing context allowlist excludes raw prompts, responses and credentials; allowed strings are bounded/redacted. The debugger adds no provider channel, analytics or raw-content persistence. Fragmented guest output is reassembled before diagnostics projection, and restored sessions preserve mission/run correlation.

Guest traces and verification commands remain authoritative. Viewing, refreshing, changing scope, or moving the historical cursor does not dispatch work, call a provider, write a mailbox, restart the runtime, edit receipts, or change acceptance state. Future replay/fork work requires its own frozen-input/provenance and side-effect contract.

## Qualification

Run `npm run test:timetravel`. It runs model/diagnostics regressions and a real Chromium test of the actual Mission Control mount. The browser test executes a real local Python Harness audit, requires a trace-bound result with zero provider calls, and passes its output through fragmented diagnostic frames. It also submits a real invalid-source request and verifies its failed run. Explicit counterexample, hostile-text and 5,000-event fixtures exercise negative cases.

The existing `npm run test:ui` now includes this qualification, so the Command Station browser CI job retains screenshots and JSON results under `runs/browser/time-travel/` alongside the existing Station evidence. `CHROMIUM_PATH` can select an installed Chromium binary; default uses Playwright's managed Chromium.

Local qualification and source hashes are recorded in `docs/testing/time-travel-local-qualification.json`. This does not substitute for hosted exact-head CI, built WebVM/WASM execution proof, independent review, or final release authorization. No merge/tag/deployment is performed by this change.

## Artwork provenance

`demo/vm/time-travel-hero.webp` was created with the built-in image-generation tool from the owner's supplied reference, then encoded to a 1024-pixel-wide WebP for delivery. Prompt: detailed shaded 16-bit dark-silver gull-wing time-machine car, both doors open, front three-quarter view facing right, phosphor-green lights and clock backdrop, wet dark ground, no UI, logos or labels. It is decorative and carries no evidence semantics.
