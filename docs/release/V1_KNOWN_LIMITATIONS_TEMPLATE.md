# RESIDUAL v1 Known Limitations and Non-Claims

**Status:** TEMPLATE. Replace placeholders only with evidence bound to the selected RC.

Release notes MUST distinguish unsupported/deferred surfaces from tested failures and untested claims.

## Platform boundaries

Planned v1 non-claims:

- native macOS x64;
- native macOS ARM64;
- Docker Desktop macOS;
- physical-iPhone heavyweight WebVM reliability.

Do not convert a lightweight iOS/WebKit walkthrough fallback into a heavyweight-WebVM reliability claim.

## Qualification boundaries

- A green unit/regression suite is not equivalent to full release qualification.
- Evidence bound to another HEAD/TREE is historical.
- A receipt proves only its encoded checks and identities.
- `SKIP`, `UNKNOWN`, `BLOCKED`, and `NOT_RUN` are not PASS.
- Automated/advisory review is not independent human assurance.

## Provider boundaries

- Local Ollama qualification does not establish hosted-provider success.
- Hosted-provider success does not establish model quality.
- A fallback response must not masquerade as success for the selected hosted provider.

## Distributed-system boundaries

Document the exact supported ownership/failure model for the selected RC. Do not imply split-brain-safe consensus, HA fencing, or hostile-filesystem guarantees unless separately qualified.

## WebVM/browser boundaries

Record the exact immutable WebVM/browser revision used by qualification. Long-run WebVM reliability and physical-device claims remain separate from desktop/browser CI.

## Research boundary

Research/AX-21/Shared-Comms evidence may inform design, but it is not release authority unless deliberately admitted to the exact RC qualification package.

## Open Core boundary

Populate from the accepted Open Core manifest, `LICENSING.md`, `NOTICE`, and license files. Do not infer commercial/enterprise distribution rights from code location alone.

## RC-specific limitations

Populate before release:

- known non-blocking defects;
- deferred integrations;
- resource ceilings;
- supported provider/model identifiers;
- deployment-profile exclusions;
- operational assumptions;
- recovery/rollback limitations.

Every item should include an evidence/reference ID where available.
