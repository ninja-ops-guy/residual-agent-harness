# RESIDUAL v1.0.0 Release Notes — TEMPLATE

> Do not publish this template as a release announcement until the exact RC has completed all mandatory gates and release authorization is recorded.

## Identity

- Release: `v1.0.0`
- Commit: `<RC_SHA>`
- Tree: `<RC_TREE>`
- Wheel SHA-256: `<WHEEL_SHA256>`
- Container digest: `<CONTAINER_DIGEST>`
- Qualification manifest: `<QUALIFICATION_DIGEST>`

## What v1 is

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Failures, unknowns, blocked states and malformed output do not silently become PASS.

## v1 release surface

Populate from the final D3 receipt. Do not claim a platform merely because development CI happened to run there.

### Required qualified surfaces

- Windows x64: `<result>`
- Linux x64: `<result>`
- Linux Docker Engine: `<result>`
- Docker Desktop Windows: `<result>`
- NVIDIA Compose overlay: `<result>`
- Chromium: `<result>`
- Firefox: `<result>`
- WebKit: `<result>`
- Local Ollama: `<result>`
- Hosted provider: `<provider/model/result>`

### Deferred / not claimed

- native macOS x64;
- native macOS ARM64;
- Docker Desktop macOS;
- physical-iPhone heavyweight WebVM reliability.

## Security and reliability evidence

- Exact-head Qualification-v1: `<receipt>`
- Independent composed-tree review: `<receipt>`
- AUD-1 F6-A: `<receipt>`
- AUD-1 F6-B: `<receipt>`
- Independent F6 adjudication: `<receipt>`
- Recovery/rollback campaign: `<receipt>`
- 24h release soak: `<receipt>`
- 72h extended soak: `<receipt or pending/non-claim>`

## Supply chain

Populate exact immutable dependencies/artifact identities from the final RC packet:

- SBOM;
- provenance/attestation;
- reproducible wheel receipt;
- container/base-image digests;
- offline dependency/wheelhouse receipt;
- Open Core/license manifest and notices.

## Known limitations

Finalize `V1_KNOWN_LIMITATIONS.md` for the selected RC and link it here.

## Upgrade / rollback

Document only procedures actually exercised by the exact-RC operational campaign.

## Evidence

Link the final `V1_EVIDENCE_INDEX.md` populated with exact-RC receipts.

## Authorization

Release publication requires explicit maintainer authorization after all mandatory gates are reconciled.
