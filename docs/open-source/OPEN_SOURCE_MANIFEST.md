# RESIDUAL Open Source Manifest

**License identifier:** Apache-2.0  
**Copyright:** 2026 Mike Olivares  
**Status:** Repository-adopted candidate funding and distribution boundary on `main`; exact-revision qualification, maintainer acceptance and legal/provenance review remain separate gates.

This file defines the deliberately narrow Apache-2.0 candidate portion of the RESIDUAL mixed-scope development monorepo. A path is included only when it is explicitly listed below, is selected by the machine-readable manifest at `docs/open-source/open-source-manifest.json`, or carries its own compatible license notice.

## Status meaning

This boundary and its machine-readable counterpart are present on `main` and are enforced by the `Open Core Boundary` workflow. The word **candidate** means that a particular export or funding package still requires exact-head qualification and explicit maintainer acceptance. It does not mean that this document is waiting to be merged.

This manifest is a scope record, not an independent legal opinion. It does not resolve historical public-license activity, contributor ownership, employment or invention-assignment obligations, third-party dependency licensing, or final distribution structure.

## Included verification/research kernel

- `ai_providers/**`
- `observation_layer/**`
- `verifier/**`
- `residual/brakes.py`
- `residual/core.py`
- `residual/extensions.py`
- `residual/goalspec.py`
- `residual/quarantine.py`
- `residual/receipts.py`
- `residual/verifier.py`

This boundary is intentionally smaller than the full RESIDUAL product. It is designed to expose reusable evidence, verification, contract, provider-abstraction, observation and policy primitives without licensing Factory, runtime orchestration, execution infrastructure, Studio, enterprise or hosted-product implementations.

## Included research and attribution material

- `CITATION.cff`
- `AUTHORS.md`
- `docs/open-source/PROJECT_ORIGIN.md`
- `docs/open-source/RESEARCH_CITATION_POLICY.md`
- `docs/research.md`
- `docs/station/RESEARCH.md`
- `docs/evaluation.md`
- `docs/controlled-evaluation.md`
- `docs/factory/SPEC-EVAL-001.md`

Publication of a specification does not imply that the corresponding implementation is included.

## Reserved examples

The machine-readable manifest is authoritative for exact export selection at a candidate revision. Reserved paths include, among others:

- Factory and engine implementations
- runtime/orchestration execution code
- sandbox execution infrastructure
- lifecycle/integration/provider implementation outside the kernel
- enterprise IAM, multi-tenancy, HA/DR, compliance and integrations
- commercial licensing/metering
- cluster/control-plane and enterprise Studio implementation

Visibility in the public monorepo is not, by itself, an Apache-2.0 license grant.

## Boundary rule

No agent, automation, funding application, documentation update or build step may expand the Apache-2.0 scope implicitly. Any expansion requires an explicit manifest change and human maintainer authorization.

## Funding rule

Open-source or research funding represented as support for RESIDUAL Open Core should be used for the included research/kernel layer unless the applicable funding agreement expressly permits another use.

Third-party and vendored material remains governed by its original license.
