# Foundation validation — 0.4.0

Executed on September 13, 2026 against the merged foundation implementation.

- **276 Python tests passed** on local Python 3.12. This includes the prior 190-test baseline, 47 imported module tests, and 39 new foundation/integration regressions. Imported tests were adapted for the closed action vocabulary, full memory hashes and explicit HITL authentication.
- **19 Chromium browser checks passed**, including desktop/mobile flows, task receipt inspection, wrapped receipt hashes at 390px, real Git integration, release download, model configuration, trace export and console-error checks. The station's SecOps and trajectory/memory hooks execute during the training mission.
- The **0.4.0 wheel built and installed into a fresh virtual environment**. An isolated Python process outside the source import path loaded the packaged provider/observation/extension modules and static/schema assets, completed all three mission tasks, validated their receipt DAG, and exported a release with no module diagnostics.
- New tests reject receipt/envelope tampering, unknown hash profiles, malformed verdicts, unknown evidence, stale verifier revisions, stale parent receipts, corrupt caches/indexes/trajectories, invalid policies, lifecycle failures, shared brake instances and concurrent registry runs. A root verifier revision change invalidates descendant caches; intact cache receipts still invoke the active verifier.
- HITL tests prove a challenge signature alone does not authorize approval, expiry/role metadata is bound, and only one of four concurrent gateway instances can consume an authenticated approval. Mesh tests use injected fixture signatures and exercise immutable payloads, duplicate rejection, key replacement rejection and receipt-reference export. They are not cryptographic interoperability or multi-device transport tests.
- SecOps tests block private-key proposals before writing and credential assignments before Git staging; untyped `"pass"` returns are rejected. NetOps tests cover missing metrics, proposal-supplied scope rejection and emergency abort before worker dispatch.

Evidence: `qa/foundation-python-tests.log`, `qa/foundation-browser-results.json`, `qa/foundation-package-results.json` and `qa/foundation-task-evidence.png`. Reproduce with `python -m unittest discover -s tests -v`, `npm run test:ui` and `python -m pip wheel --no-deps .`.

The PR's existing GitHub workflows run the Python 3.11/3.12/3.13 matrix, package/CLI checks, Chromium workflows and Docker build/demo. Their status is reported by the PR checks; historical baseline CI evidence in `VALIDATION.md` does not establish a new commit's status.

No real Ollama model, GPU runtime, paid cloud inference, network device executor, authenticated mesh transport, production deployment, measured token savings, zk/TEE, TPM or formal CRDT proof was exercised. Existing provider async/streaming behavior is retained; Bedrock streaming remains unsupported. See the [implementation boundaries](../roadmap/TRACK-1-IMPLEMENTATION.md).
