# Read This First for Demo / Provider Changes

The 2026-09-17 provider regression passed deterministic provider tests because those tests intentionally replaced the real Puter SDK. Production then failed at the browser-policy/network layer.

Therefore every agent must preserve these independent proofs: exact deployed SHA, WebVM `/demo/` isolation and guest behavior, `/provider/` non-isolation, deterministic provider protocol fixtures, published real Puter SDK loading, real auth/inference when claimed, and physical-device behavior when claimed.

Start with repository `AGENTS.md`, then `DEMO_REGRESSION_GUARDRAILS.md`, `TEST_MATRIX.md`, and `DO_NOT_MERGE_DEMO.md`.
