# RESIDUAL

**Evidence-bound acceptance and control for autonomous systems.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering and autonomous systems. Workers, models, tools, and external systems may produce candidate work; **the harness owns acceptance**. Candidate outputs are bound to evidence and provenance, independently checkable conditions can be applied, and only accepted state is allowed across controlled integration boundaries.

> **A worker may propose a state transition. It does not get to declare that transition valid.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## Why RESIDUAL exists

As autonomous systems become capable of modifying code, infrastructure, security controls, business systems, and other consequential environments, the problem is no longer only whether an agent can perform a task.

The harder questions are:

- What actually happened?
- Which exact execution and candidate produced the evidence?
- Does that evidence remain valid after failure, restart, retry, or recovery?
- Did an independent verifier confirm the conditions required by the acceptance contract?
- Who has authority to allow the resulting state transition?

RESIDUAL is designed around those questions.

```text
Models / Agents / Tools
          |
          v
     Candidate Work
          |
          v
   Evidence + Provenance
          |
          v
 Independent Verification
          |
          v
 Acceptance Authority
          |
          v
 Qualified State Transition
```

## Core model

RESIDUAL separates **execution** from **authority**.

Workers may reason, call tools, modify artifacts, collaborate, recover from failures, and propose results. Worker completion alone does not establish an accepted result.

```text
Candidate
   |
   v
Evidence
   |
   v
Challenge
   |
   v
Verification
   |
   v
Authority
   |
   v
Accepted State
```

The objective is not to make unreliable computation disappear. It is to prevent worker failure, provider interruption, stale or replayed evidence, duplicate results, candidate identity drift, transport faults, partial execution, verifier errors, or incorrect completion claims from silently becoming accepted state.

## Competitive boundary

RESIDUAL is not primarily another chatbot framework, prompt library, model router, or replacement for existing agent frameworks. Models and agent frameworks can operate as execution substrates beneath RESIDUAL's evidence and acceptance controls.

The trust boundary is intentionally above the individual model or worker:

**Agents produce candidates. Evidence establishes what happened. Verifiers challenge the evidence. Authority decides what becomes state.**

This makes provider and framework independence more than a routing concern: a provider response, worker completion, or external-system claim is evidence about an execution, not automatic authority over system state.

## Distributed and self-hosting direction

RESIDUAL's distributed execution work is aimed at allowing specialized workers to communicate, replace failed workers, recover, challenge results, and operate across hosts while preserving evidence and acceptance boundaries.

A longer-term self-hosting direction is governed self-development:

```text
Requirement
    |
    v
Distributed Work
    |
    v
Candidate Change
    |
    v
Independent Challenge
    |
    v
Verification
    |
    v
Qualification
    |
    v
Human / Host Authority
    |
    v
Accepted Change
```

This is not a claim of unrestricted recursive self-modification or autonomous merge authority. The intended model is that autonomous systems may propose, implement, test, and challenge changes without unilaterally authorizing them.

## Enterprise direction

The same architecture can extend to enterprise systems while those systems remain authoritative. Governed evidence adapters can expose observations and claims; separately permissioned action paths can control mutations.

Potential integration domains include ERP, CRM, MES, QMS, ITSM, IAM, SIEM/security platforms, observability, databases and data warehouses, document systems, and collaboration platforms.

The architectural goal is an evidence fabric in which raw observations, derived facts, external claims, RESIDUAL-generated claims, verifier results, and authority decisions retain distinct provenance instead of collapsing into a single trusted agent response.

## Maturity path

The immediate objective remains a narrowly defined, reproducible v1 with qualified release invariants. Post-v1 maturity work should not delay v1 unless new evidence demonstrates violation of an existing v1 invariant or release criterion.

The intended post-v1 sequence is:

**exact release qualification -> performance and verification-tax characterization -> provider qualification -> qualification control plane/analytics -> independent operator reproduction -> bounded enterprise pilot**

That sequence is intended to answer not only whether RESIDUAL works, but what additional assurance costs and whether an independent operator can reproduce the same qualified behavior.


## Licensing and editions

RESIDUAL is being structured as an **open-core** project. The candidate Apache-2.0 component is a deliberately small **verification and research kernel**, not the complete runtime or enterprise platform. This development repository contains reserved product code, so GitHub visibility is not itself a license grant.

See [LICENSING.md](LICENSING.md) and the exact-revision [Open Source Manifest](docs/open-source/OPEN_SOURCE_MANIFEST.md) before relying on license scope.

Factory execution, engine/runtime orchestration, sandbox execution, enterprise identity, multi-tenancy, HA/DR, compliance, commercial licensing, cluster/control-plane and enterprise Studio implementations remain reserved unless explicitly added to an accepted manifest.

## Citation and project origin

RESIDUAL was created and is maintained by **Mike Olivares (`ninja-ops-guy`)**. For software or research use, cite the exact version/commit through [CITATION.cff](CITATION.cff). The public provenance record is in [PROJECT_ORIGIN.md](docs/open-source/PROJECT_ORIGIN.md), and research-significant releases should preserve immutable revisions, evidence digests, and DOI-backed archives when available.

AI coding and research systems are used extensively as development tools; human authorship, licensing authority, research claims, and integration authority remain with the human maintainer and credited human contributors.

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution, fail-closed runtime handling, fresh-overlay recovery, privacy-safe local diagnostics, and an iOS/WebKit pre-boot walkthrough fallback.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main

Current `main` is **`4608afabf5de4c87d77aaf149dfc12538d364f43`**.

Two accepted changes landed since the previous documented snapshot:

- **#200** — native setup hardening. The setup path now defaults to persistent XDG state, binds Station to `127.0.0.1`, makes the convenience shell macro opt-in, uses bounded venv repair, and constrains shell startup-file edits. This is onboarding hardening, **not** blank-environment qualification or a portability proof.
- **#205** — WebVM provider-channel recovery. Mission Control now restores the private provider channel token from `sessionStorage` across reload/remount, validates it fail-closed, reuses it only for the active browser session, and clears it on explicit close. This is accepted provider-session lifecycle behavior, **not** retained proof of live Puter inference.

The exact-current-main Actions set observed for `main@4608afa...` is complete with no pending, cancelled, or failing run in the retained exact-SHA query; the sampled Controller/provider workflow is **PASS on attempt 1**. Those results remain scoped to their named automated gates. They do not establish every-host/capable-runner M4 qualification, physical iPhone reliability, blank-environment install, host-loss recovery, elapsed soak, live-provider semantic success, or confirmatory research.

Historical failures remain evidence even when later revisions pass.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded build-output path, #183 repaired provider-session lifecycle behavior, #189 repaired the provider-helper publication boundary, and #205 now restores the provider channel across Mission Control reload/remount. None of those changes, by itself, is retained proof of successful paid/live Puter inference. A fresh real-account mission on the accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain open.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research evidence boundary

Research results are revision-bound and deliberately mixed:

- Draft #202 retains an earlier heterogeneous-DAG **FAIL** and a later distinct exact-head bounded **PASS** using real local models for a three-task DAG with forced repair. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.
- Draft #203 M6 ImprovementSpec self-host trial 1 remains **FAIL**.
- Draft #204 stronger-model M6-SPEC-002 authoritative trial remains **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no verification receipt or release.
- Draft #207 deterministic stress campaign B retained important negative governance evidence: one budget-exhaustion case observed accepted integration/release before final exhausted-budget accounting, and one terminal verifier-failure case still materialized a non-empty release. A repeated-repair case rejected injected corrupt candidates and integrated none, but did not recover to task success within the pass budget.

These are research/development observations, not production qualification. See [`docs/research.md`](docs/research.md) and [`docs/evaluation.md`](docs/evaluation.md).

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

1. Repair and requalify the stress-campaign governance-ordering defects before making stronger fail-closed budget/release claims.
2. Retain a fresh real-account Puter candidate→verifier→receipt success on the accepted deployed revision, or keep live-provider success `UNKNOWN`.
3. Physically validate the #186 mobile fallback without broadening it into a heavyweight-WebVM reliability claim.
4. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak for the exact release artifact.
5. Continue #120/#126 long-run WebVM reliability work and the separate #139→ownership-baseline→#134 protected sequence.
6. Resolve the #133/#132 retirement-versus-restoration discrepancy explicitly rather than reconstructing capability in prose.
7. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5 and the planned degradation/routing studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, autonomous recursive self-improvement, autonomous merge authority, or live proof of the central research hypothesis.