# OpenAI open-source program application readiness

**Status:** Candidate reviewer brief — not a submitted application, award, approval or acceptance of terms  
**Prepared:** 2026-11-13  
**Maintainer:** Mike Olivares (`ninja-ops-guy`)  
**Repository:** `ninja-ops-guy/residual-agent-harness`  
**Candidate base revision:** `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`

This document prepares a truthful, narrowly scoped package for OpenAI open-source maintainer, funding and defensive-security programs. Program availability, eligibility, benefits and terms must be re-checked on the official OpenAI pages immediately before submission.

Nothing in this document expands the Open Core, licenses reserved implementation, assigns IP, authorizes testing of third-party systems or accepts program terms.

## Project summary

RESIDUAL is an evidence-first research and engineering project for making AI-assisted software work more verifiable. Workers may propose bounded work, but the harness owns acceptance: execution is observed, evidence is retained, candidate outputs are checked against explicit verifier contracts, and only accepted state is allowed across controlled integration boundaries.

The proposed Open Core is a deliberately small verification and research kernel. It exposes reusable provider-abstraction, observation, evidence, receipt, verification and policy primitives so researchers and maintainers can reproduce experiments and test reliability mechanisms without opening the complete RESIDUAL product.

The public repository is a mixed-scope development monorepo. Factory execution, runtime orchestration, sandbox infrastructure, Studio, control-plane, enterprise and hosted-service implementations remain reserved.

## Why the work is relevant

AI coding systems can generate useful work quickly, but confidence in a generated patch, report or execution trace should not rest on model assertion alone. RESIDUAL investigates whether useful system-level reliability can emerge from bounded delegation, retained evidence, verifier-defined acceptance, explicit failure states and deterministic integration controls even when individual model calls remain fallible.

The project is especially relevant to open-source maintenance where limited maintainer time, heterogeneous model behavior, supply-chain risk and reproducibility requirements make evidence quality and acceptance authority consequential.

## Authoritative scope

The exact candidate Open Core is defined by:

- `docs/open-source/open-source-manifest.json` — machine-readable include/exclude selection;
- `docs/open-source/OPEN_SOURCE_MANIFEST.md` — human-readable scope and boundary rules;
- `LICENSING.md` — licensing and funding-disclosure interpretation; and
- `docs/open-source/COMMERCIAL_BOUNDARY.md` — reserved commercial layer.

The designated candidate license is Apache-2.0. Repository visibility is not itself a license grant, and an application must not describe the whole monorepo as Apache-2.0.

## Requested support and intended use

Subject to the current program terms, support would be used only for the manifest-listed kernel and openly documented research unless an applicable agreement expressly permits a broader use. Appropriate work includes:

1. reproducible model comparisons across bounded engineering tasks;
2. verifier, receipt and evidence-integrity regression testing;
3. fault injection, malformed-output and abstention/failure-path testing;
4. maintenance automation, issue/PR review assistance and release preparation;
5. exact-revision export qualification and dependency review;
6. documentation, examples and reproducibility artifacts; and
7. authorized defensive review and patch validation of project code where separately approved.

Support would not be represented as funding for reserved enterprise or hosted-product development. No employer system, customer environment, confidential dataset or third-party target is part of this request.

## Expected public outcomes

A scoped support period should produce inspectable outputs rather than an activity count alone:

- an exact-revision Open Core archive with retained digest and qualification evidence;
- a published evaluation protocol and revision-bound model comparison results;
- retained negative findings and failed trials, not only successful runs;
- expanded adversarial and malformed-output regression fixtures;
- clearer maintainer workflows and contribution documentation; and
- a concise report identifying what the evidence does and does not establish.

Outcomes should be linked to immutable commits or releases. Test counts, PR counts and model activity must not be presented as substitutes for adoption or independent assurance.

## Existing qualification machinery

The `Open Core Boundary` GitHub Actions workflow runs on relevant pull requests and performs:

- adversarial exporter fixture tests;
- open/reserved boundary validation;
- committed-snapshot export selection;
- static Python import-closure analysis;
- immutable source-archive construction; and
- isolated smoke imports from the exported archive.

A passing run establishes only those named checks at its exact head. It does not prove ownership, legal validity, dynamic-import completeness, security, production fitness, broad adoption or the central research hypothesis.

## Current strengths

- A public, actively developed implementation exists rather than a proposal-only repository.
- The open/reserved boundary is machine-readable and fail-closed.
- The project retains explicit `FAIL`, `UNKNOWN` and `BLOCKED` outcomes instead of silently converting them to success.
- Citation, origin, contribution, security, funding-disclosure and provenance records exist.
- Research claims are revision-bound and negative evidence is preserved.
- Maintainer authority is separated from automated qualification.

## Material limitations to disclose

- RESIDUAL is early-stage and must not be presented as widely adopted without external evidence.
- The full platform is not Apache-2.0; only the manifest-scoped candidate kernel is in scope.
- Automated qualification plus maintainer review is not independent assurance.
- Historical public-license, employment/invention-assignment and contributor-provenance questions have not received an independent legal audit.
- A packaged Open Core release still requires exact-head qualification, retained artifact/digest evidence, dependency/SBOM review and maintainer acceptance.
- The project does not claim universal correctness, blanket production readiness, security certification or autonomous merge authority.

## Draft application answer

> RESIDUAL Open Core is an evidence-first verification and research kernel for AI-assisted engineering. Workers may propose bounded work, while verifier-defined acceptance, retained evidence and receipts control what can cross integration boundaries. The open kernel exposes provider abstraction, observation, evidence, verification and policy primitives for reproducible reliability research.
>
> I am seeking support for open maintenance, exact-revision qualification, model comparisons, fault-injection and malformed-output testing, maintainer automation, documentation and published research artifacts. Expected outputs include a qualified source archive, reproducible evaluation protocols, retained positive and negative results, expanded regression fixtures and a concise evidence report.
>
> The public repository is a mixed-scope monorepo. This request covers only the manifest-listed Apache-2.0 candidate verification/research kernel. Factory execution, runtime orchestration, sandbox infrastructure, Studio, enterprise, control-plane and hosted-service implementations remain reserved. The project is early-stage and does not claim broad adoption, independent security certification, universal correctness or blanket production readiness.

## Submission package checklist

- [x] Public repository identified.
- [x] Maintainer and project origin identified.
- [x] Narrow Open Core and reserved scope identified.
- [x] Intended use of credits/support limited to eligible open work.
- [x] Material technical, adoption and provenance limitations disclosed.
- [x] No confidential employer, customer or third-party material included.
- [x] No third-party security target or unauthorized testing proposed.
- [ ] Final PR head passes the complete `Open Core Boundary` workflow.
- [ ] Maintainer reviews the final exact-head diff and CI evidence.
- [ ] Current official program terms and application fields are re-verified.
- [ ] Maintainer authorizes submission.
- [ ] Submission receipt is retained without implying acceptance or approval.

## Authority boundary

Only the human maintainer may approve the exact Open Core boundary, authorize submission, accept program terms, make legal representations, or accept an award. Automation may prepare evidence and draft application text but may not perform those authority actions implicitly.
