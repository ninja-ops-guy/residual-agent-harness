# INT-008: in-toto / SLSA Provenance Integration Spec

## Metadata
- **ID**: INT-008
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (evidence bundle), M4 (trust boundary), INT-002 (external signing)
- **Protected boundaries**: Receipt semantics, verifier authority, M4 evidence, disclosure policy

## Problem

An evidence artifact can describe a run without proving the build/deployment lineage of the software that produced it.

## Goal

Emit version-pinned in-toto statements and SLSA-compatible **build provenance** for release/evidence-producing artifacts, while treating source-control assurance as a separate source-track claim. Provenance proves lineage, not model/result correctness.

## Non-Goals

- Replacing RESIDUAL receipts or M4 evidence
- Treating SLSA level terminology as verifier correctness
- Claiming a source or build level that has not been independently checked against the pinned SLSA specification version
- Using legacy "SLSA 4 = two-person review" language as the current model

## Design

### Track separation

The implementation records explicit target tracks:

- **Build provenance**: builder identity, source/material digests, build invocation and produced artifact digests.
- **Source assurance**: repository/source-management controls, if separately evaluated.

A claim MUST name the SLSA spec version, track and level, e.g. `SLSA vX.Y Build L3-compatible`. Source and Build levels are not collapsed into one number.

### Version-pinned statement

Use the current pinned in-toto Statement and SLSA provenance predicate versions selected at implementation time. Do not hardcode older predicate URLs in the normative spec. The provenance generator records:

```json
{
  "statement_spec": "pinned",
  "predicate_spec": "pinned",
  "subject": [{"name": "artifact", "sha256": "..."}],
  "builder_identity": "...",
  "source_commit": "...",
  "source_tree": "...",
  "materials": [{"uri": "...", "digest": {"sha256": "..."}}],
  "build_workflow_identity": "...",
  "build_parameters_digest": "..."
}
```

INT-002 may sign the provenance/attestation sidecars. Signing does not itself elevate the SLSA level.

### in-toto chain

If an in-toto layout is used, steps represent actual retained operations (for example checkout/build/package/sign/publish). No synthetic `verify` step is inserted merely to make the chain look complete.

## Interfaces

```python
class ProvenanceGenerator:
    def generate(self, artifact: Path, context: BuildContext) -> ProvenanceEnvelope: ...
    def verify(self, artifact: Path, envelope: ProvenanceEnvelope) -> "ProvenanceVerdict": ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Subject binding: artifact digest matches provenance subject |
| T2 | Source binding: commit/tree/material identities are retained |
| T3 | Tamper: artifact or provenance modification fails verification |
| T4 | Builder: wrong builder/workflow identity fails policy verification |
| T5 | Track discipline: Build and Source claims are emitted separately |
| T6 | Level check: a version-pinned conformance checker justifies any stated SLSA level |
| T7 | Authority: provenance/signature cannot create RESIDUAL acceptance |

## Failure Modes

| Failure | Behavior |
|---|---|
| Build/source context incomplete | no qualified provenance claim; UNKNOWN/BLOCKED |
| Provenance verification fails | INVALID/reject for policies requiring provenance |
| Spec-version conformance cannot be established | do not state a SLSA level |

## Exit Criteria

- [ ] Build and Source tracks are separated
- [ ] Current pinned SLSA/in-toto schema versions are used at implementation time
- [ ] Any level claim is backed by an executable conformance record
- [ ] INT-002 signatures remain external to RESIDUAL acceptance semantics
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
