# RESIDUAL v1 recovery qualification contract

Status: **review-only release preparation**. This document does not authorize a
backup, restore, rollback, deployment, traffic change, canary, physical test, or
release.

## Purpose

This contract prepares the machine-verifiable evidence boundary for the v1
production-readiness findings:

- **PR-G07** — prove a versioned backup/restore path and measured RPO/RTO;
- **PR-G21** — prove rollback against the exact release candidate and prior
  deployable artifact without losing data or authority invariants.

It is intentionally downstream of an owner-approved v1 deployment profile and an
exact selected release candidate. It cannot be used to infer those decisions.

## Existing HADR code is not production evidence

`residual/hadr/backup.py` and `residual/hadr/restore.py` are useful implementation
and test inputs, but main explicitly describes the stdlib backup crypto as an
offline-simulation construction and recommends a production AEAD provider.
`BackupManager.backups` is also an in-process list, not a durable production
backup repository. Therefore unit tests of those modules are **not** accepted as
proof that PR-G07 or PR-G21 passed for v1.

The release gate requires retained evidence from a separately authorized,
production-shaped exercise against the approved deployment profile and the exact
RC artifact.

## Evidence contract

`scripts/validate_v1_recovery_evidence.py` accepts one
`residual.v1-recovery-evidence.v1` JSON object. A PASS requires all of the
following:

1. **Exact RC binding**
   - 40-hex commit and tree;
   - SHA-256 of the deployable RC artifact.
2. **Approved deployment profile**
   - content hash of the approved profile;
   - explicit approval bit.
3. **Declared objectives**
   - approved RPO and RTO, in seconds.
4. **Backup evidence**
   - application-consistent backup identifier and manifest digest;
   - encryption is asserted and only a non-secret key *reference* is retained;
   - readability proven before any traffic change;
   - at minimum: database, durable outbox/journal, evidence/receipt store, and
     configuration references.
5. **Restore evidence**
   - exact binding to the declared backup;
   - UTC start/end timestamps after backup creation;
   - integrity, receipt-chain, application-startup, and critical-read checks;
   - observed RPO and RTO at or below approved objectives.
6. **Rollback evidence**
   - prior artifact digest differs from the RC;
   - procedure, data integrity, authority integrity, and in-flight-work policy
     are all verified.
7. **Evidence retention**
   - immutable evidence-index digest and verified independent copy.
8. **Human qualification authority**
   - named Qualification Lead, explicit approval, and UTC approval timestamp.

Malformed or incomplete evidence is `BLOCKED`. A well-formed observed exercise
that violates a safety or recovery requirement is `FAIL`. Only complete,
observed, objective-satisfying evidence is `PASS`.

The validator performs validation only. It never creates or decrypts a backup,
restores data, manipulates traffic, selects an RC, deploys an artifact, or grants
release authority.

## Required future execution

Before PR-G07 / PR-G21 can become `VERIFIED`:

- approve the v1 deployment profile (V1-PP-001 / PR #432 or accepted successor);
- select the exact post-convergence RC;
- execute a separately authorized production-shaped backup and restore drill;
- exercise the bounded rollback path to the previous deployable artifact;
- retain raw evidence and an immutable index;
- have the Qualification Lead review and approve the exact evidence;
- validate the retained bundle with this contract or an accepted successor.

No synthetic fixture, unit test, HADR simulation, CI-only run, or prose report can
substitute for that execution evidence.
