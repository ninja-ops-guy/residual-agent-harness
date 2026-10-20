# INT-002: Sigstore / Cosign External Evidence Signing Spec

## Metadata
- **ID**: INT-002
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (evidence bundle), M4 (trust boundary)
- **Protected boundaries**: Receipt semantics, verifier authority, M4 evidence, disclosure policy

## Problem

RESIDUAL evidence can be internally hash-bound yet still lack a portable external signature that another party can verify against a known CI/workload identity.

## Goal

Create an external Sigstore/Cosign signature over the **exact finalized evidence artifact bytes** (or their canonical digest) without changing RESIDUAL's canonical receipt or acceptance semantics.

## Non-Goals

- Replacing RESIDUAL receipt signing or verifier authority
- Treating a Sigstore signature as evidence that the underlying result is correct
- Mutating an evidence bundle after it has been signed
- Requiring the public service for every deployment; private/offline trust roots are a later deployment choice

## Design

### Finalize-then-sign

1. RESIDUAL finishes the canonical evidence artifact.
2. Compute SHA-256 over the exact retained bytes.
3. Sign the artifact as a **blob** using a pinned Sigstore/Cosign flow (for example `cosign sign-blob`) or an equivalent library API.
4. Retain the Sigstore verification bundle/signature as a **sidecar** so signing does not change the bytes being signed.
5. Record signer identity, issuer, artifact digest, tool/version and transparency-log proof when available.

Illustrative CLI shape (exact flags are pinned by the implementation lockfile/tool version):

```bash
cosign sign-blob --yes --bundle evidence.sigstore.json evidence-bundle.json
cosign verify-blob \
  --bundle evidence.sigstore.json \
  --certificate-identity "$EXPECTED_IDENTITY" \
  --certificate-oidc-issuer "$EXPECTED_ISSUER" \
  evidence-bundle.json
```

### ExternalSignatureReference

```json
{
  "schema": "residual.external-signature.v1",
  "artifact_sha256": "...",
  "signature_type": "sigstore",
  "signature_bundle_sha256": "...",
  "signer_identity": "...",
  "signer_issuer": "...",
  "signing_tool": "cosign",
  "signing_tool_version": "pinned",
  "transparency": {
    "present": true,
    "log_id": "...",
    "log_index": 123456
  }
}
```

This reference may be included in a higher-level manifest, but the canonical evidence artifact being signed remains immutable.

## Interfaces

```python
class SigstoreSigner:
    def sign_blob(self, artifact: Path) -> ExternalSignatureReference: ...
    def verify_blob(self, artifact: Path, reference: ExternalSignatureReference) -> "SignatureVerdict": ...
```

`SignatureVerdict` is `VALID`, `INVALID`, or `UNVERIFIABLE`. Network/trust-material failure is not the same as a cryptographically invalid signature.

## Test Plan

| Test | Description |
|---|---|
| T1 | Exact bytes: finalized artifact digest is recorded before signing |
| T2 | Verify: matching artifact + signer identity verifies |
| T3 | Tamper: one-byte artifact change fails verification |
| T4 | Identity: wrong expected identity/issuer fails |
| T5 | Sidecar: signature material does not mutate the signed artifact |
| T6 | Offline bundle: retained verification bundle is sufficient where the pinned Sigstore flow supports offline verification; otherwise result is UNVERIFIABLE, never VALID |
| T7 | Authority: valid signature cannot create verifier PASS, receipt acceptance or integration |

## Failure Modes

| Failure | Behavior |
|---|---|
| Signing service/OIDC unavailable | no external signature; artifact remains unsigned and explicitly marked so |
| Signature verification fails cryptographically | INVALID |
| Trust material/network required but unavailable | UNVERIFIABLE |
| Transparency proof missing when policy requires it | BLOCKED/UNVERIFIABLE |

## Exit Criteria

- [ ] Exact finalized bytes are signed as a blob
- [ ] Signature/proof retained separately and hash-bound
- [ ] Tamper and identity tests pass
- [ ] Signature validity cannot change RESIDUAL acceptance authority
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
