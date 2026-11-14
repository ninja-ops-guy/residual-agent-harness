# Open-source funding readiness

**Application package:** PREPARED FOR EXACT-HEAD CI AND MAINTAINER REVIEW — NOT SUBMITTED  
**Open-core export/release:** CANDIDATE — NOT YET CERTIFIED  
**Legal/commercial readiness:** REVIEW REQUIRED BEFORE MATERIAL COMMERCIALIZATION OR A FORMAL PACKAGED RELEASE

The goal is to make funding claims narrow, reproducible and consistent with the commercial boundary. Application readiness is intentionally separated from packaged-release certification and from legal/commercial review.

## What may proceed before full commercialization review

A maintainer may seek open-source or research support for the manifest-listed verification/research kernel when all of the following are true:

1. the application identifies the exact public repository and the narrow manifest scope;
2. the proposed use of support is limited to open maintenance, evaluation, reproducibility, qualification, model comparison and published research unless the agreement expressly permits more;
3. the application does not characterize the full mixed-scope monorepo as Apache-2.0;
4. the application discloses material unresolved technical, adoption and provenance limitations; and
5. accepting the applicable terms would not expand the license boundary, transfer reserved IP or authorize work outside the maintainer's rights.

Application materials:

- reviewer-facing project brief: `docs/open-source/OPENAI_APPLICATION_READINESS.md`;
- public-safe, field-by-field form draft: `docs/open-source/OPENAI_APPLICATION_FORM_DRAFT.md`.

Private account fields must be entered directly by the maintainer in the official form and must not be committed to the public repository.

## Technical boundary gates

- [x] Machine-readable include/exclude boundary exists.
- [x] Human-readable scope and reserved-layer rules exist.
- [x] Open-core archive selection is pinned to an immutable Git snapshot.
- [x] Export rejects untracked/staged working-tree bytes, unsafe paths, symlinks, submodules, reserved-path leakage and overwrite.
- [x] Static import-closure CI exists to detect local dependencies crossing outside the proposed license scope.
- [x] Isolated source-archive smoke qualification exists.
- [ ] The final application-candidate PR head passes the complete `Open Core Boundary` workflow.
- [ ] The maintainer reviews and accepts that exact passing head for the application.

A passing workflow establishes only the checks it runs: adversarial export fixtures, boundary consistency, committed-snapshot selection, static Python import closure, immutable archive construction and isolated archive smoke imports. It does not prove ownership, legal validity, dynamic-import completeness, security, production fitness or downstream adoption.

## Distribution and release gates

These are required before presenting a packaged Open Core release as certified; they do not all block a truthful, narrowly scoped funding application.

- [ ] Produce and retain the exact-revision source archive and its digest.
- [ ] Reconcile release notes and public status claims to the selected revision.
- [ ] Complete the required protected-branch qualification and maintainer attestation.
- [ ] Complete the transitive dependency and SBOM review for the packaged artifact.
- [ ] Preserve immutable citation/research references for a research-significant release.

## Legal and provenance gates

- [x] Apache-2.0 text is retained in-repo.
- [x] Citation and project-origin records exist.
- [x] CONTRIBUTING, security and provenance policies exist.
- [x] Funding disclosure policy separates public application material from reserved/confidential material.
- [ ] Historical public-license activity reviewed for actual legal effect.
- [ ] Employment and invention-assignment obligations reviewed.
- [ ] Contributor copyright/provenance reviewed; DCO is not treated as an assignment.
- [ ] Final distribution and commercialization structure reviewed as appropriate.

Unresolved items must remain disclosed. This checklist is an engineering/governance record, not legal advice or an independent IP audit.

## Allowed funding description

Describe RESIDUAL Open Core as the project's **open verification and research kernel for evidence-bound AI-assisted engineering**. State that workers may propose bounded work while verifier-defined acceptance, retained evidence and receipts control integration.

Do not describe the complete RESIDUAL runtime, Factory, Studio, enterprise product, control plane, hosted service or every publicly visible file as Apache-2.0.

## Appropriate uses of support

Unless the applicable agreement expressly permits broader use, open-source funding, model access or API credits represented as support for RESIDUAL Open Core should be used for:

- maintenance and review of the manifest-listed kernel;
- reproducible evaluations and model comparisons;
- verifier, receipt, evidence and policy-primitives testing;
- regression, fault-injection and malformed-output testing;
- documentation, examples and maintainer automation;
- exact-revision qualification and openly documented research artifacts.

## Adoption and assurance claims

Use external adoption evidence separately from engineering velocity. PR counts, test counts, model activity and agent activity are not substitutes for users, downstream projects, contributors, stars, forks or citations.

Describe the project as **maintainer-reviewed with automated qualification**. Do not claim independent assurance, universal correctness, blanket production readiness or security certification without claim-specific evidence.

## Submission authority

- [ ] Maintainer has reviewed the final application text.
- [ ] Maintainer has reviewed the applicable current program terms.
- [ ] Maintainer has authorized submission from the exact qualified revision.
- [ ] Application receipt or status has been recorded without implying approval.

No automation or documentation change may check these authority items on the maintainer's behalf.
