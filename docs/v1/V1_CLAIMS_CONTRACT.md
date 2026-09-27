# RESIDUAL v1.0.0 Claims Contract

**Status:** PROPOSED — OWNER APPROVAL REQUIRED  
**Release:** v1.0.0  
**Source baseline:** `main@d796f36b75e730a0bab71bdba564206174393719`

This is a **decision document, not a design specification**. It defines what
v1.0.0 promises and explicitly does not promise. A claim is releasable only when
its row in `V1_CLAIMS_VERIFICATION_MATRIX.md` has acceptance evidence bound to
the exact release candidate.

## Proposed v1 promises

1. **Authority boundary.** Workers may propose work; they do not self-approve or
   gain Station integration authority. Verification/review/integration remains
   on the trusted Station side.
2. **Operator/tenancy model.** v1 is a trusted single-user/local-operator
   product. It does not claim hardened multi-tenant isolation or an
   Internet-facing multi-user service.
3. **Station exposure.** Direct Station service exposure is loopback-only.
   Trusted remote workers may be used only through an approved authenticated
   transport consistent with the documented SSH-tunnel/HTTPS model and the
   final AUD-1 qualification. Direct unauthenticated/untrusted network exposure
   is not supported.
4. **Remote-worker authority.** Remote workers are bounded to explicitly enabled
   worker access and scoped work. Credential revocation/rotation, stale
   authority rejection, and bounded authority loss must satisfy the selected
   AUD-1 successor and its physical F6 evidence before release.
5. **Persistence.** v1 uses a single authoritative Station persistence domain
   with SQLite-backed state and Git-backed candidate/integration state.
   Exactly-once atomicity across the SQLite/Git boundary is **not** claimed;
   documented operator recovery may be required after an interrupted boundary.
6. **Station concurrency.** One authoritative Station process owns a given v1
   data directory at a time. Multi-process Station ownership and multi-host
   shared-database operation are not v1 claims and must fail closed if attempted.
7. **Shared Comms recovery.** v1 may claim receipt-first recovery only if the
   accepted successor proves that a local ACK is semantically bound to the
   expected project/operation and required payload/actor identity, and that a
   stored payload is digest-verified before recovery can POST.
8. **Recovery ownership.** Concurrent recovery owners for the same outbox are
   **not supported in v1**. The release candidate must enforce single-owner
   recovery or reject a second owner; documentation alone is insufficient.
9. **High availability / disaster recovery.** v1 does not claim automatic
   failover, multi-host shared-database HA, or regional failover. Backup/restore
   claims are limited to the owner-approved deployment profile and must meet its
   declared RPO/RTO.
10. **Release artifact.** v1 ships only for the owner-approved
    OS/architecture/Python/artifact/extras matrix. That matrix becomes the input
    to PR-G28; the release dependency set must be exact-pinned, hash-locked and
    proven installable/buildable under the approved offline-build procedure.
11. **Qualification.** Historical R4.1 `READY_FOR_CANARY` remains a scoped
    historical qualification, not production acceptance. v1 requires the
    claims-verification matrix to be green on one exact RC.
12. **Soak.** The exact RC must complete an owner-approved elapsed soak. Proposed
    default: **72 continuous hours**. Any code, dependency, configuration, or
    release-artifact change that affects a claim under soak resets the applicable
    soak clock unless the approved soak contract explicitly proves it irrelevant.

## Explicit v1 non-promises

v1.0.0 does **not** promise hardened multi-tenancy, arbitrary direct
Internet-facing Station deployment, concurrent outbox recovery, multi-process
ownership of one Station data directory, multi-host shared SQLite, automatic
host/region failover, exactly-once SQLite/Git atomicity, universal platform
support, or correctness of unqualified live-provider behavior.

R5, enterprise, HA/DR, multi-tenant, experimental, and research implementations
present in the repository do not become v1 promises merely because code or tests
exist.

## Decisions required for approval

Owner/operations approval must freeze these values before this contract can be
`APPROVED`:

- exact OS + architecture + Python + installation-artifact + optional-extras
  matrix for PR-G28;
- exact authenticated remote-worker transport admitted by v1;
- backup/retention policy, availability objective, RPO and RTO;
- exact soak duration/environment/workload/evidence cadence and reset rule;
- whether Shared Comms is a release claim. If yes, claims 7 and 8 are
  pre-release gates; if no, Shared Comms must be disabled/excluded by enforceable
  release configuration rather than documentation alone.

Approval of this document does not approve #438, authorize the canary, supply a
human attestation, approve a deployment, or authorize release.
