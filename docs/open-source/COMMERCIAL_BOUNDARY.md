# RESIDUAL commercial boundary

RESIDUAL uses an open-core architecture.

## Open layer

The open layer exists to make reliability research reproducible and to provide a useful developer/runtime foundation. It includes selected runtime primitives, evidence/receipt formats, verifiers, evaluation tooling, research corpora, and reproducibility infrastructure.

The authoritative license scope is `OPEN_SOURCE_MANIFEST.md`.

## Reserved commercial layer

Commercial differentiation is intentionally reserved around organizational operation of RESIDUAL, including:

- enterprise identity, SSO/SCIM and organization policy
- multi-tenancy
- HA/DR and fleet/cluster operation
- compliance reporting and audit export
- enterprise integration hub
- enterprise control-plane capabilities
- enterprise Studio capabilities
- managed hosting and hosted control services
- premium operational automation, support and commercial integrations
- commercial licensing/metering

Public documentation of an idea or interface does not automatically place implementation in the Apache-2.0 Open Core.

## Product principle

The open core should remain useful enough for independent reproduction, local experimentation and community development. Commercial value should come from operating, governing and scaling RESIDUAL for organizations rather than artificially crippling research reproducibility.

## Migration

Existing mixed public code remains in this monorepo while the boundary is stabilized. Future releases should package the open-core distribution from the manifest and keep reserved enterprise development in a separately controlled repository/distribution.
