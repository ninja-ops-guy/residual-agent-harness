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

Current `main` is **`d89c5d940a32d8a7df4dd55e699c158fff5f615c`**, produced by merged **#336** on 2026-09-19. Immediately before it, merged **#337** landed PR-Agent advisory-governance hardening at `5c98e2cccae0d10478462bb42be6b280301bf978`.

Recent accepted changes relevant to current claims remain deliberately scoped:

- **#307** — removes duplicate generic feature-branch `push` fan-out while preserving PR qualification and non-cancelling production-main evidence.
- **#260** — accepts the provider-bootstrap guard that keeps the Puter load control disabled until its private bridge is initialized. This is bounded UI/transport behavior, not paid/live Puter evidence.
- **#288** — closes #208 with host-owned pre-dispatch budget/deadline admission for Station runner/reviewer dispatch plus run-control-bound export eligibility. Historical #207/#212 negative research cells remain retained and require claim-specific requalification rather than being rewritten as PASS.
- **#320** — adds repository-side CSP/anti-clickjacking hardening. Production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328/#330** — accept scoped runtime/source security hardening and GitHub Actions checkout credential-persistence hardening. These are not blanket security qualification.
- **#337** — makes PR-Agent advisory publication fail closed by requiring a substantive full-review marker and separates review/status concurrency so a bot failure/status comment cannot stand in for a completed advisory.
- **#336** — adds an explicit guest-filesystem durability boundary (`os.sync()`) before Mission Control/WebVM publishes reusable worker completion. This is a scoped durability repair; it does not itself establish production Pages PASS.

Every new `main` SHA is required by accepted #276 to receive its own non-cancelling first production Pages attempt. For exact current main `d89c5d94...`, production Pages run **`35449637725`**, attempt 1, completed **FAIL**. Generated desktop+narrow browser proof, deployment, published desktop exact-revision/real-guest execution, and multiple narrow live-guest stages passed. The required narrow Chromium path nevertheless failed at a later compound retained-evidence assertion. That assertion chains existence checks for the live/build/follow-up artifacts plus `verify_run(...)` for all three mission directories, so this retained attempt does **not** identify which subpredicate failed first. The lower-level cause is therefore **UNKNOWN** and must not be attributed to Puter/model quality, Factory/M4, provider transport, or another subsystem without further evidence.

The retained live-proof artifact is **`webvm-live-proof-35449637725-1`** with SHA-256 **`edd0d84e1270b71cc53039cae85e42041c06767c52039bb6c418a3ffffd62ff8`**. The #336 durability boundary is therefore **necessary but insufficient** for the full narrow reload/evidence acceptance path. The next changed-head repair should split the compound retained-evidence assertion into independently reported existence and `verify_run(...)` checks without weakening either requirement, then repair the first observed failing invariant. Do not rerun unchanged `main@d89c5d94...` merely to obtain green.

Production Pages run `35431634267`, attempt 1, remains a scoped **PASS for exact revision `0a675017...` only**. The production Pages FAIL on `3bfa6aba...` and earlier `e7b72ad...` also remain retained exact-revision evidence. Historical failures remain evidence even when later revisions pass.

Two open candidates are not accepted current-main capability. **#338** is rebased onto current main and changes protected `RuntimeJournal` bytes plus the Factory ownership baseline; it remains unaccepted and requires explicit trust-boundary review, never automatic merge. **#340** contains the implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw provider/runtime adapters and remains unaccepted. Its research/evaluation material was split into draft **#341**, `EXP-NESTED-SWARM-001`, which is explicitly research-only and must not be treated as accepted provider or production capability.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged provider/session/bootstrap/publication changes do not substitute for fresh live semantic evidence. A fresh real-account mission on an accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain open.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

Qualification-v1 is a separate branch evidence path. Open **#152** has advanced to exact testing-branch head **`aeba9962918c3659693e1efcd5603275cfb77cb4`**. Its first exact-head `RESIDUAL Qualification v1` run **`35448856959` attempt 1 remains FAIL**. Real bubblewrap sandbox provisioning itself passed, as did self-tests, toxic-provider, M4, browser, discovery, concurrency, fault-injection and the other named sibling jobs visible in the retained run; the required **deterministic** job still failed at `Full deterministic regression gate`, and the fail-closed aggregate therefore also failed. The visible retained summary does not by itself establish a lower-level causal diagnosis for the deterministic regression failure. #152 remains open/unaccepted and its maintainer/advisory governance is not satisfied. Predecessor runs remain historical exact-head evidence only.

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

Describe that as **maintainer-reviewed with automated qualification**. It is not independent human assurance. Claim-specific independent or third-party evidence remains required wherever a security, release or research claim depends on it.

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

1. Diagnose the exact-current-main production Pages **FAIL** by splitting the narrow retained-evidence compound assertion into independently reported existence and `verify_run(...)` predicates without weakening any acceptance condition; retain run `35449637725` attempt 1 as authoritative FAIL for `d89c5d94...`.
2. Resolve #152's remaining deterministic Qualification-v1 **FAIL** on `aeba996...` while preserving the now-working real bubblewrap provisioning and all fail-closed requirements. Do not rerun an unchanged head merely for green.
3. Treat **#338** as a protected trust-boundary candidate only; its RuntimeJournal/ownership-baseline changes require explicit independent review and must never be auto-merged.
4. Keep **#340** implementation-only and **#341** research-only until each satisfies its own exact-head evidence and governance path; neither is current-main provider/research proof.
5. Requalify stronger budget/unknown-usage/release-ordering claims against the accepted #288 repair; historical frozen failures remain visible.
6. Rebase and requalify #323 before any first authoritative Research Workbench trial.
7. Validate the merged #320 policy on the production Vercel origin before calling response-header remediation PASS in production.
8. Retain a fresh real-account provider candidate→verifier→receipt success on an accepted deployed revision, or keep live-provider success `UNKNOWN`.
9. Complete physical mobile fallback validation, true blank-environment installation, recovery/host-loss qualification, selected elapsed soak, and #120/#126 long-run WebVM reliability work without broadening bounded evidence.
10. Keep M6/M7 research bounded: general recursive self-improvement and general mesh efficiency remain `UNKNOWN`; M6-008 remains `BLOCKED`.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, autonomous recursive self-improvement, autonomous merge authority, production Vercel security-header validation, or live proof of the central research hypothesis.