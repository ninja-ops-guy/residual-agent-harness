# Validation record — Command Station 0.3.0

## Executed in this build environment

- **190 Python tests passed:** the original harness/station suite, supplied observation/control tests, and provider, observation and control-integrity regressions.
- **17 browser workflow assertions passed** in a real headless Chromium browser, including a 1440px desktop view and 390px mobile view.
- The training mission creates actual Git candidates, runs behavioral Python checks, refreshes a disjoint parallel candidate, reviews, integrates a dependent third task, and downloads a source release ZIP.
- Tests cover immutable goal/action values, goal hash authority/lineage, amendment limits, once-only quarantine release, denied/foreign/forged holds, concurrent release, policy errors, loop budgets without worker events, spoofed observations, unknown usage, abort priority, final-pass success, persisted run receipts, manifest/path/cycle validation, strict LDD events, event chains, report checkpoints, concurrent exclusive claims, lease recovery, stale results, scoped writes, failed checks, changed candidates, stale approvals, rebase/review, pause/cloud permission, call reservations, key redaction, command opt-in, and artifact integrity.
- Real loopback HTTP fixtures exercise all seven provider routes, sync/async streaming, tool payloads, reported/cache usage, malformed responses, rate limits, failover, partial-stream failures, request reservations and safe diagnostics. Bedrock signing matches an independent botocore SigV4 reference for an escaped ARN and temporary session token. HTTP API tests check Host/Origin/session enforcement, remote candidate idempotency, and worker/operator separation.
- Browser tests check onboarding, progress, task evidence, release download, escaped operator notes, persisted model settings, setup access, valid/invalid Markdown feedback, provider credentials/failover, run-control evidence and saved budgets, mobile overflow, trace integrity/filter/export/pause controls, diagnostics and console errors.
- Python package build and an isolated installed-wheel demo succeeded; static assets and JSON schema resources are included in the wheel. The isolated installed wheel also completes the real three-task station demo through the new goal controller and verifies its observation chain. Results are in `qa/package-results.json`.

Browser screenshots and the machine-readable result are in `docs/station/qa/`. The tests are reproducible with `python -m unittest discover -s tests -v` and `npm run test:ui` (Playwright is a development-only dependency).

## Execution environment and limits

The executed checks used Linux, Python 3.12 and headless Chromium. The Python 3.11/3.13 CI matrix is configured but was not run here. Control token and time limits are cooperative wave boundaries; they do not cancel an in-flight executor.

## Not executed here

- No real Ollama model was downloaded or run; native GPU/Metal/CUDA inference and memory capacity require validation on the target hardware.
- No paid cloud model calls were made. Model reasoning quality, completion rates and real token/cost savings remain unmeasured.
- Docker is unavailable in this environment, so the included image and CPU/NVIDIA Compose launches were not built/run here. The CI workflow includes a Docker build and in-container demo check for a Docker-capable environment.
- macOS and Windows native launcher/runtime installation were inspected but not run on those operating systems.
- Multi-machine TLS networking, very long soak tests, production deployment, and adversarial OS sandbox evaluation are outside this build's executed evidence.

The scripted training mission is clearly labeled in the UI. Passing tests and model review are evidence of specified checks, not a proof of general correctness or production readiness.
