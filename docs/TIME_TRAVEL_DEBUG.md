# Mission Control Time Travel Debugging

Time Travel Debugging is a read-only Mission Control view over the existing privacy-sanitized local diagnostic buffer. It lets an operator scrub through a retained run or the whole browser session and reconstruct the diagnostic state that was visible at each recorded event.

## Trust boundary

Time Travel does **not** rewrite, delete, or amend guest evidence. It does **not** execute a historical prompt, repeat provider calls, or claim deterministic program replay. The retained guest trace and verification commands remain authoritative execution evidence. Time Travel is a debugging projection over sanitized browser-local diagnostics.

That distinction is intentional: a developer can inspect historical state without granting the browser UI authority to mutate M3 receipts, M4 integration state, provider budgets, or side effects.

## What is reconstructed

For each selected event the view derives the point-in-time mission status, run and mission identity, runtime health, provider lifecycle stage/model, evidence-event count and last projected evidence kind, UI state projections, failure classification, and release binding. A delta panel shows exactly which reconstructed fields changed from the preceding event.

The timeline can be scoped to the latest run, another retained run, or the full session. Back/forward controls and a scrubber move through immutable snapshots derived from the event log.

## Source and privacy

The feature consumes the existing `DemoDiagnostics` bounded buffer. That buffer already applies allow-listed context keys, length limits, URL stripping, and secret redaction before persistence. Time Travel adds no new provider or network channel and stores no additional raw prompt or provider response content.

## Non-goals

Execution replay, filesystem rollback, reissuing provider requests, reproducing side effects, and branching a historical mission are deliberately out of scope for this first integration. Those features would require a separate replay contract that binds frozen inputs, environment identity, tool/provider budgets, and side-effect suppression to a new derived run rather than pretending the old run changed.
