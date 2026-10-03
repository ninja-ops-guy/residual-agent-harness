# RESIDUAL v1 deployment-scope decision

Status: **UNAPPROVED / owner-operations input required**.

This worksheet exists to close master-ledger item `V1-PP-001`. It is not a deployment configuration and does not authorize a canary, merge, production exposure, release, or change to any frozen R4/R4.1 artifact.

A production qualification gate may be marked `NOT_APPLICABLE` only when an approved field below explicitly excludes the corresponding claim. `UNDECIDED` is fail-closed and leaves dependent gates `BLOCKED`.

## 1. Release profile identity

| Field | Decision |
|---|---|
| profile_id | `UNDECIDED` |
| profile_version | `UNDECIDED` |
| intended release | `v1.0.0` |
| decision owner | `UNDECIDED` |
| operations owner | `UNDECIDED` |
| approval timestamp | `UNDECIDED` |
| approved source revision | `UNDECIDED` |

## 2. Network and trust boundary

Select and document one supported v1 claim; do not infer a broader claim from implementation capability.

| Field | Allowed decision / required detail | Decision |
|---|---|---|
| Station exposure | `LOOPBACK_ONLY`, `PRIVATE_NETWORK`, or `INTERNET_FACING` | `UNDECIDED` |
| Station bind addresses | exact supported bind set | `UNDECIDED` |
| reverse proxy | `NONE` or named/versioned supported proxy topology | `UNDECIDED` |
| TLS termination | `NONE_LOCAL_ONLY`, `STATION`, or named trusted proxy boundary | `UNDECIDED` |
| proxy-header trust | exact trusted-hop/header policy or `NONE` | `UNDECIDED` |
| certificate policy | issuer/hostname/validation/downgrade policy or `NOT_APPLICABLE` | `UNDECIDED` |
| remote workers | `DISALLOWED` or exact supported trust/network topology | `UNDECIDED` |
| outbound provider access | supported provider/network boundary or `DISALLOWED` | `UNDECIDED` |

## 3. Principal and tenancy model

| Field | Allowed decision / required detail | Decision |
|---|---|---|
| operator model | `SINGLE_TRUSTED_OPERATOR` or explicitly defined multi-operator model | `UNDECIDED` |
| user model | `LOCAL_OPERATOR_ONLY`, `SINGLE_TENANT_MULTI_USER`, or `MULTI_TENANT` | `UNDECIDED` |
| authorization boundary | exact principal/role/project policy | `UNDECIDED` |
| break-glass authority | named role/process or `NOT_SUPPORTED` | `UNDECIDED` |
| credential custody | local OS trust domain, external secret manager, or other exact contract | `UNDECIDED` |

## 4. Supported runtime and persistence envelope

A platform not explicitly listed here is not a v1-supported production platform.

| Field | Decision |
|---|---|
| operating system(s) and version(s) | `UNDECIDED` |
| CPU architecture(s) | `UNDECIDED` |
| Python version(s) | `UNDECIDED` (project minimum is >=3.11; support set must be narrower or equal) |
| installation artifact | `WHEEL`, `CONTAINER`, or explicitly versioned alternative: `UNDECIDED` |
| filesystem(s) | `UNDECIDED` |
| SQLite version / delivery source | `UNDECIDED` |
| SQLite durability mode | `UNDECIDED` |
| persistent-volume semantics | `UNDECIDED` |
| multi-process Station | `SUPPORTED` or `DISALLOWED`: `UNDECIDED` |
| multi-host shared database | `SUPPORTED` or `DISALLOWED`: `UNDECIDED` |

## 5. Service objectives and recovery claims

No reliability/DR gate can be declared passed against an unspecified objective.

| Objective | Decision |
|---|---|
| availability/SLO window | `UNDECIDED` |
| maximum planned operation/recovery time | `UNDECIDED` |
| RPO | `UNDECIDED` |
| RTO | `UNDECIDED` |
| backup frequency/retention | `UNDECIDED` |
| evidence/audit retention | `UNDECIDED` |
| log retention/disk budget | `UNDECIDED` |
| host-loss claim | `NONE`, restore-only, or failover contract: `UNDECIDED` |
| regional-loss claim | `NONE` or explicit contract: `UNDECIDED` |
| approved burn-in/soak duration and environment | `UNDECIDED` |

## 6. Qualification applicability rules

These rules classify applicability; they do not mark a gate PASS.

- `PR-G05` remote TLS/proxy qualification is mandatory for `PRIVATE_NETWORK` or `INTERNET_FACING`. It may be `NOT_APPLICABLE` only for an approved `LOOPBACK_ONLY` profile with no trusted-proxy claim.
- `PR-G17` externally reachable rate-limit qualification is mandatory when untrusted or multi-user clients can reach Station. A trusted local-only profile must explicitly state why the exposure is excluded before this gate can be `NOT_APPLICABLE`.
- `PR-G31` host/region-loss qualification applies only to recovery/failover claims selected above. Unsupported HA/region-loss behavior must be explicitly excluded from v1 product claims rather than silently treated as PASS.
- `PR-G09` multi-process/multi-host ownership qualification is mandatory if either topology is supported. If both are disallowed, boot/deployment validation must prove the unsupported topology fails closed or is operationally prevented.
- `PR-G12`, `PR-G15`, `PR-G07`, and release soak/recovery acceptance thresholds are derived from the approved SLO/RPO/RTO values above; no threshold may be back-filled after observing test results.
- Security, evidence-integrity, artifact provenance, clean-install, rollback, corruption, secret-leak, configuration, audit, incident-response, and exact-release binding gates remain applicable even for a loopback-only profile unless a separate reviewed requirement explicitly says otherwise.

## 7. Owner approval receipt

Approval must bind this completed worksheet to exact bytes and release planning state.

Record, outside any secret-bearing channel:

- SHA-256 of the completed approved worksheet;
- repository commit/tree containing the approved worksheet or immutable external decision artifact;
- approving owner identity and operations authority;
- approval timestamp;
- exact master-ledger revision reviewed;
- explicit statement that `UNDECIDED` does not remain in any field used by an applicable release gate.

The approval receipt authorizes qualification against this scope only. It is not a release GO or deployment authorization.

## Completion gate for `V1-PP-001`

`V1-PP-001` becomes `VERIFIED` only when all of the following are true:

1. every field material to an applicable v1 claim is decided;
2. contradictions between network, tenancy, persistence, and recovery claims are resolved;
3. gate applicability is mechanically reviewed against `PR-G01..PR-G33`;
4. the decision is content-addressed and owner/operations approved before dependent tests are interpreted;
5. no test outcome was used to weaken the scope or objective after the fact.
