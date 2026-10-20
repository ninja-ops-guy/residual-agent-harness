# INT-017: SPIFFE / SPIRE Workload Identity Spec

## Metadata
- **ID**: INT-017
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (identity/evidence binding), M4 (trust boundary)
- **Protected boundaries**: Receipt semantics, signer authority, verifier authority, M4 evidence, disclosure policy

## Problem

Distributed workloads need short-lived, auditable service identity. Manual static credentials are difficult to rotate and do not provide a standard workload-identity namespace.

## Goal

Use SPIFFE/SPIRE to authenticate RESIDUAL worker/verifier/integrator workloads and bind that identity into execution/evidence records **without silently changing canonical receipt-signing semantics**.

## Non-Goals

- Replacing the canonical receipt schema or signing authority
- Treating possession of an SVID as verifier acceptance authority
- Embedding private workload keys into evidence
- Requiring SPIFFE for single-process/local deployments

## Design

### Workload identity

```text
spiffe://residual.local/ns/<namespace>/sa/<service-account>
```

`SPIFFEIdentityProvider` returns an authenticated workload identity/trust-bundle revision to the host. Host authorization maps permitted SPIFFE IDs to roles. The mapping is version/hash bound.

```python
@dataclass(frozen=True)
class WorkloadIdentityEvidence:
    spiffe_id: str
    trust_domain: str
    trust_bundle_sha256: str
    svid_not_before: str
    svid_not_after: str
    workload_role: str
```

### Signing boundary

Canonical RESIDUAL receipts continue to use the currently accepted receipt/signing contract. If a deployment wants an SVID-backed external signature, it signs a **versioned identity attestation envelope** that references the canonical receipt hash. Promoting SVID signing into the canonical receipt schema requires a separate receipt-version spec and migration/compatibility tests.

## Interfaces

```python
class SPIFFEIdentityProvider:
    def current_identity(self) -> WorkloadIdentityEvidence: ...
    def authorize_role(self, expected_role: str) -> bool: ...
    def trust_bundle_identity(self) -> str: ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | SVID: workload obtains short-lived identity from Workload API |
| T2 | Role mapping: only allowed SPIFFE IDs map to worker/verifier/integrator role |
| T3 | Rotation: identity renewal does not change stable role semantics within the frozen trust policy |
| T4 | Expiry: expired/untrusted SVID is rejected |
| T5 | Trust drift: trust-bundle revision change is detected/version-bound |
| T6 | Receipt boundary: SPIFFE identity cannot alter canonical receipt schema or acceptance authority |
| T7 | Optionality/non-interference: disabling SPIFFE preserves local baseline behavior where identity is not required |

## Failure Modes

| Failure | Behavior |
|---|---|
| SPIRE unavailable when identity required | BLOCKED/fail closed |
| SVID expired/untrusted | reject identity |
| Trust bundle changed unexpectedly | require explicit host re-evaluation; no silent continuation |
| Wrong role/ID | reject authorization |

## Exit Criteria

- [ ] Workload identity is authenticated and evidence-bound
- [ ] Trust-bundle revision retained
- [ ] Canonical receipt signing is unchanged unless separately versioned
- [ ] Rotation/expiry/role tests pass
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
