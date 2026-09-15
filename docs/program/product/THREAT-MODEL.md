# Residual trust-boundary threat model

**Version 1; reviewed baseline in [README](README.md).** This is a scoped security
argument and test plan. A mechanism listed below is not a claim that every attack
against it has been blocked; qualification must retain exact-tree evidence.

## Assets, principals and trust assumptions

Protected assets are accepted source/artifacts, Station policy and capability
grants, frozen plans/contracts, signing identities, durable evidence history,
HITL decisions, model credentials, host data, availability and measured research
claims. Confidentiality, integrity and availability are distinct obligations.

Trusted computing base: host kernel and process supervisor; Residual controller,
Station authority and integrator; configured policy/signing-key custody; chosen
verifier implementation for its declared semantic checks; authoritative storage;
operator authentication; explicitly loaded plugins and runtime dependencies.
Cloud/local providers, worker text, candidate code and external evidence are
untrusted inputs. A verifier may execute untrusted candidate code, so its *execution*
requires isolation even though its decision logic has an authority role.

A signing key proves an identified issuer committed to bytes. It does not prove
those bytes are correct or that a dishonest issuer reported every event. Hashes
detect changed bytes only relative to a trusted retained reference. A fully
rewritten log can require an independent external anchor to detect.

## Boundaries and admissible effects

| Boundary | Permitted influence | Must not confer |
| --- | --- | --- |
| User intent → frozen mission/plan | Authenticated policy-scoped goals; explicit revisions | Arbitrary worker reinterpretation of authority |
| Provider → worker proposal | Candidate content and usage observations | New tools, cloud disclosure or acceptance permission |
| Worker → broker/workspace | Contract-scoped bounded files/actions | Host credentials, arbitrary filesystem/network/OS access |
| Candidate → verifier | Isolated evidence and test input | Host escape, verifier binary replacement, policy mutation |
| Verifier → M4 | Typed result bound to exact inputs/revision/output | PASS by stdout convention, missing/UNKNOWN becoming success |
| M4 → accepted-state publisher | Validated signed decision over verified tree | Unfenced publication, replayed second acceptance |
| Authority stores → observers | Read-only metrics, dashboards and cursor-fed projections | Authoritative state transitions from metrics |
| Operator → HITL gateway | Authenticated challenge-specific one-use response | Role text alone or replay authorization |
| Export → researcher/reproducer | Versioned artifacts, provenance and declared omissions | Claims beyond retained independent evidence |

## Threat inventory

| Attacker / failure | Attack or consequence | Mechanism / intended response | Limitation and qualification requirement |
| --- | --- | --- | --- |
| Malicious worker | Prompt injection, forged capability, path escape, unauthorized network/tool use | Frozen WorkerContract, host broker, seccomp process restrictions, budgets, lease checks; violation terminates and remains unaccepted | Current brokered Python scope is narrower than arbitrary SDK/shell execution; red-team each advertised backend |
| Malicious candidate code | Host read/write via tests, executable replacement, symlink/hardlink or TOCTOU, process survival | Isolated verifier execution and immutable snapshot/tree binding are required; escape attempt fails closed | M4 base is not qualified; #81 audit, namespace/proc/dev/socket/fd tests and post-verification mutation tests remain gates |
| Faulty or colluding verifier | Semantically wrong patch passes, weak assertion, hidden regression, flaky result | Independent ground-truth adversarial corpus, verifier revision binding, quality estimates and UNKNOWN separation | Isolation prevents host effects, not incorrect judgments; correlated/colluding verifiers can all be wrong |
| Compromised provider | Dishonest content/usage, prompt injection, outages, switched model identity | Provider outputs remain proposals; Station policy and verification remain authoritative; record model/route and usage provenance | Cannot establish provider internals, honest billing or training-data privacy; independent usage reconciliation required |
| Compromised host/kernel | Rewrite memory, bypass sandbox, steal signing keys, alter receipts/logs | Detect inconsistent retained artifacts where independent anchors survive | Out of threat tolerance; no protection claim against root/kernel compromise or compromised TCB |
| Dishonest operator | Approve malicious policy, omit failed runs, rewrite history, use valid signing key dishonestly | Frozen protocol, authenticated approvals, exported signed/hash-anchored evidence and independent audit | Local operator is a trust anchor; cannot force honest experiment disclosure or stop authorized key misuse without external governance |
| Tampered evidence | Forged receipt, altered artifacts, missing/stale parents, log truncation/reordering | Strict JSON/hash validation, Station signature on consumption, queue chain, root/result binding; missing/unverifiable remains unaccepted | Unsigned/unanchored roots do not prove completeness; stale override authority and parent binding require audit |
| Git corruption | Missing/truncated object, crafted path/mode, accepted tree differs from verified tree | Validate objects/tree evidence and bind exact verified snapshot; classify unreadable evidence UNKNOWN/error | #63/#81 qualification pending; no promise to repair corrupt Git automatically or treat an error as empty content |
| Network attacker | MITM, replay, theft of tokens, stale/duplicate delivery | Authenticated transport, provider TLS, bounded requests and scoped tokens; DSM fencing/idempotency/ack protocol required | Deployment transport/key management and all connector implementations require review; network partition may sacrifice availability |
| Resource exhaustion | Fork/output bombs, huge DAG/artifact/filename, sparse files, disk full, hanging verifier | Process/byte/time limits, safe artifact admission, capacity/backpressure and evidence deadlines; fail closed | Host-wide quotas/cgroups and sustained scale limits need environment-specific proof; no unbounded availability claim |
| Malicious plugin/dependency | Import-time execution, authority bypass, supply-chain substitution | Review/pin trusted plugins, supply-chain manifest/signatures, isolate where explicitly supported | Dynamically loaded in-process plugins are trusted code; interface checks alone do not sandbox them |
| Stolen/replayed HITL response | Reuse approval or claim privileged role text | HMAC-bound durable challenge, host authenticator, expiry, atomic consume, role and goal binding | MAC is not user authentication; actual action/resume must have separate idempotent durable coupling |

## Security invariants and test evidence

1. Non-PASS results, absent evidence and storage errors cannot authorize acceptance.
2. Verified tree bytes and accepted tree bytes agree, including paths/modes and
   trusted executable inputs; a passing process exit alone is insufficient.
3. Worker/provider text cannot create capabilities or bypass Station policy.
4. Every accepted transition resolves to contracts, plan, worker/evidence receipts,
   verifier revision/results and workload identity by validated references.
5. Lease expiry, retry, restart, duplicate delivery and lost acknowledgements do not
   create a second acceptance or reuse an exhausted HITL authorization.
6. Metrics remain projections; losing monitoring cannot silently change authority,
   and losing required evidence storage cannot be hidden by healthy monitoring.
7. No claim of semantic correctness is inferred from a valid receipt signature.

For each tested threat, retain attacker input/corpus ID, expected invariant,
observed result, affected identities/trees, exit/termination classification,
resource counters, before/after host sentinels, retained evidence and tool versions.
Label UNSUPPORTED, SKIPPED and UNKNOWN separately from blocked attacks. A seven-case
containment suite is evidence for those cases, not a general escape-proof claim.

## Deployment scope and review triggers

This proposal initially supports single trusted-host authority; multi-node operation
needs DSM qualification. Separate provider credentials and Station signing keys,
restrict durable-store permissions, bind management endpoints to the intended
network and authenticate remote access. Do not expose a development/stub surface
as a hardened public control plane without explicit review.

Re-review when adding a worker backend, verifier execution profile, privilege,
namespace/mount exception, network connector, artifact type, dependency/plugin,
receipt schema, storage backend, observer write path or accepted-state publisher.
Changes to the TCB or policy invalidate inherited qualification until targeted
adversarial evidence covers the new boundary.
