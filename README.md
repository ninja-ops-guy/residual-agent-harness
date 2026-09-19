# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution, fail-closed runtime handling, fresh-overlay recovery, privacy-safe local diagnostics, and an iOS/WebKit pre-boot walkthrough fallback.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main

Current `main` is **`2f9dda3882f39c28a1c766859b1bf9579eea7911`**, produced by merged **#338** on 2026-09-19. Immediately before it, merged **#336** landed the Mission Control/WebVM evidence-durability repair and **#337** landed the PR-Agent advisory-governance hardening.

Recent accepted changes relevant to current claims remain deliberately scoped:

- **#307** — removes duplicate generic feature-branch `push` fan-out while preserving PR qualification and non-cancelling production-main evidence.
- **#260** — accepts the provider-bootstrap guard that keeps the Puter load control disabled until its private bridge is initialized. This is bounded UI/transport behavior, not paid/live Puter evidence.
- **#288** — closes #208 with host-owned pre-dispatch budget/deadline admission for Station runner/reviewer dispatch plus run-control-bound export eligibility. Historical #207/#212 negative research cells remain retained and require claim-specific requalification rather than being rewritten as PASS.
- **#320** — adds repository-side CSP/anti-clickjacking hardening. Production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328/#330** — accept scoped runtime/source security hardening and GitHub Actions checkout credential-persistence hardening. These are not blanket security qualification.
- **#337** — makes PR-Agent advisory publication fail closed by requiring a substantive full-review marker and separates review/status concurrency so a bot failure/status comment cannot stand in for a completed advisory.
- **#336** — adds an explicit guest-filesystem durability boundary (`os.sync()`) before Mission Control/WebVM publishes reusable worker completion.
- **#338** — accepts a bounded contention-only retry for the idempotent `RuntimeJournal` constructor admission phase and advances the protected Factory ownership pin for `residual/factory/runtime_journal.py` to the reviewed blob. Non-contention errors and deadline exhaustion remain fail-closed. This is a scoped protected-byte change, not blanket Factory/M4 or every-host qualification.

The exact #338 PR head had a matching maintainer attestation, but its PR-Agent advisory was **FAIL / unavailable** because the configured OpenAI review models returned `credit_balance_exhausted`. That failed advisory is retained as missing advisory evidence and must not be reinterpreted as substantive review.

Every new `main` SHA is required by accepted #276 to receive its own non-cancelling first production Pages attempt. For exact current main `2f9dda38...`, production Pages run **`35452581203`**, attempt 1, completed **PASS**. Generated desktop+narrow browser proof passed; deployment passed; published desktop exact-revision/real-guest execution passed; and the published narrow-Chromium verification passed. No rerun was used.

The retained live-proof artifact is **`webvm-live-proof-35452581203-1`** with SHA-256 **`eed4f0722e43af9362eb62bad122de3521e6f391d92b6388b582c92ef1bff63f`**. This is a scoped PASS for the publication/browser/real-guest acceptance path on this exact revision only. It does **not** establish paid/live provider semantic success, model quality, blank-environment installation, host-loss recovery, elapsed soak, physical heavyweight-WebVM iPhone reliability, every-host M4 qualification, or independent review.

Historical first-attempt outcomes remain revision-bound evidence. In particular, `d89c5d94...` run `35449637725` attempt 1 remains **FAIL** at the narrow retained-evidence path with lower-level cause **UNKNOWN**; `3bfa6aba...` and `e7b72ad...` retain their own exact-revision FAIL results; and `0a675017...` run `35431634267` attempt 1 remains a scoped PASS for that predecessor revision. The new PASS does not erase those retained failures.

Two open candidates are not accepted current-main capability. **#340** contains the implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw provider/runtime adapters and remains unaccepted. Its research/evaluation material is split into draft **#341**, `EXP-NESTED-SWARM-001`, which is explicitly research-only and must not be treated as accepted provider or production capability.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged provider/session/bootstrap/publication changes do not substitute for fresh live semantic evidence. A fresh real-account mission on an accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and the historical reload/persistence failure tracked by #335 remain relevant reliability evidence even though exact-current-main Pages now passes.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. Merged #338 is now another explicit protected sequence: `RuntimeJournal` protected bytes changed, the Factory ownership baseline was advanced to the reviewed blob, and current-main Factory ownership CI is green. That sequence authorizes only the reviewed bounded constructor-admission behavior; it does not broaden M4, verifier, evidence-schema, sandbox, release, or every-host claims. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent.

Qualification-v1 is a separate branch evidence path. Open **#152** remains at exact testing-branch head **`aeba9962918c3659693e1efcd5603275cfb77cb4`**. Its first exact-head `RESIDUAL Qualification v1` run **`35448856959` attempt 1 remains FAIL**. Real bubblewrap sandbox provisioning itself passed, as did self-tests, toxic-provider, M4, browser, discovery, concurrency, fault-injection and the other named sibling jobs visible in the retained run; the required **deterministic** job still failed at `Full deterministic regression gate`, and the fail-closed aggregate therefore also failed. The visible retained summary does not by itself establish a lower-level causal diagnosis for the deterministic regression failure. #152 remains open/unaccepted and must reconcile with current `main` before any merge-readiness claim; predecessor runs remain historical exact-head evidence only.

## Research evidence boundary

Research results are revision-bound and deliberately mixed:

- #220 / M6-SPEC-006 remains a bounded corrected-path self-hosting **PASS**; earlier M6 self-host trials retain **FAIL** evidence.
- #257 / M6-SPEC-007J is a bounded autonomous-discovery **PASS at formal MeasurementGap admission**. Later registry/provenance/planner experiments retain PASS, FAIL and UNKNOWN cells. General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**.
- #207/#212 retain historical accounting/release-ordering and failure-matrix evidence. The accepted #288 repair closes the product defect tracked by #208, but it does not retroactively change those frozen outcomes; affected stronger claims require fresh repaired-path requalification.
- #319 / M6-MESH-001 is one positive bounded two-obligation concurrency pilot; general mesh/swarm efficiency remains **UNKNOWN / not established**.
- Draft #323 Research Workbench remains **BLOCKED for its first authoritative trial** pending rebase and requalification onto a main containing #288.
- Draft #341 is a governed nested-runtime research track only; its existence is not evidence of nested-swarm benefit or accepted provider capability.

M6-008 remains **BLOCKED** until its declared semantic/derivation gates are satisfied. These are research/development observations, not production qualification. See [`docs/research.md`](docs/research.md) and [`docs/evaluation.md`](docs/evaluation.md).

## Governance boundary

Merged **#168** establishes the repository's solo-maintainer control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

Describe that as **maintainer-reviewed with automated qualification**. It is not independent human assurance. Claim-specific independent or third-party evidence remains required wherever a security, release or research claim depends on it. The #338 PR-Agent capacity failure remains explicit evidence that automated advisory review was not satisfied for that merge and must not be rewritten as PASS.

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

With Docker running, the launcher serves the Station UI at `http://localhost:8765`. Native mode requires Python 3.11+ and Git:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

The accepted `setup.sh` path is an optional native convenience path; it does not remove the Python 3.11+ host prerequisite or constitute blank-machine qualification.

See [`START-HERE.md`](START-HERE.md) for installation and operator setup.

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

## Current priority gates

1. Preserve current exact-main Pages run **`35452581203` attempt 1 = PASS** as scoped evidence and retain predecessor FAILs, especially `d89c5d94...` run `35449637725`; continue #335/#120/#126 reliability work without treating one green revision as a long-run reliability proof.
2. Resolve #152's remaining deterministic Qualification-v1 **FAIL** on `aeba996...`, then reconcile/requalify the testing branch against current `main`, including the accepted #338 protected RuntimeJournal/ownership-baseline change. Do not rerun an unchanged failed head merely for green.
3. Keep **#340** implementation-only and **#341** research-only until each satisfies its own exact-head evidence and governance path; neither is current-main provider/research proof.
4. Requalify stronger budget/unknown-usage/release-ordering claims against the accepted #288 repair; historical frozen failures remain visible.
5. Rebase and requalify #323 before any first authoritative Research Workbench trial.
6. Validate the merged #320 policy on the production Vercel origin before calling response-header remediation PASS in production. Current Vercel deployment-rate failures do not establish product or header behavior.
7. Retain a fresh real-account provider candidate→verifier→receipt success on an accepted deployed revision, or keep live-provider success `UNKNOWN`.
8. Complete physical mobile fallback validation, true blank-environment installation, recovery/host-loss qualification, selected elapsed soak, and #120/#126/#335 long-run WebVM reliability work without broadening bounded evidence.
9. Keep M6/M7 research bounded: general recursive self-improvement and general mesh efficiency remain `UNKNOWN`; M6-008 remains `BLOCKED`.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, autonomous recursive self-improvement, autonomous merge authority, production Vercel security-header validation, substantive PR-Agent advisory review for #338, or live proof of the central research hypothesis.
