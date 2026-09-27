# Security Review Package (ENT7-R3)

> **REFERENCE TEMPLATE — NOT CURRENT V1 SECURITY EVIDENCE.** This document describes an enterprise review-package target. It does not establish scan results, penetration-test completion, independent assurance, support commitments, or controls for the current v1 candidate. Any populated result must bind to an exact source/artifact identity, tool/configuration, timestamp, retained report, and applicable deployment profile.

Requirement: **ENT7-R3** — Residual MUST provide a security review package
including a threat model, attack surface analysis, mitigation strategies,
compliance mapping (per SPEC-ENT-002), vulnerability scan results (per
SPEC-ENT-005), and penetration test results.

## 1. Threat Model (STRIDE)

Assets: task contracts, receipts (integrity evidence), HITL approvals,
module code, credentials used by engine adapters, customer data in task
payloads.

| Threat | Category | Vector | Mitigation |
|---|---|---|---|
| Forged receipts | Tampering | Attacker modifies receipt store | SHA-256 hash chain; `hash_id` validation; verify-on-read |
| Replayed approvals | Spoofing | Reuse of HITL approval tokens | Per-challenge nonces; approval receipts bound to task ID |
| Malicious module | Elevation of privilege | Install of backdoored module | Install-time validation, quarantine, rollback (ENT7-R4); module allowlist |
| Prompt-injected task output | Tampering / Info disclosure | Engine output smuggles instructions | At the verification boundary, model output is candidate data and is not trusted merely because a model produced it. Generated/derived code may execute only on explicitly documented execution surfaces, each with its own authority and containment boundary |
| Secret exfiltration | Information disclosure | Engine adapter leaks credentials | Secret handling plus profile-specific egress/observation controls. Do not infer a universal egress block or complete observation coverage unless the exact execution surface/profile is qualified |
| Denial of service | DoS | Task flood, verifier CPU exhaustion | Rate limits, task quotas, brake thresholds |
| Log/receipt repudiation | Repudiation | Operator denies an approval | Hash-chained receipt trail provides tamper-evident linkage. Authenticated authorship/non-repudiation requires separate signature/MAC and trust-anchor evidence |

## 2. Attack Surface Analysis

| Surface | Exposure | Hardening |
|---|---|---|
| Station API/CLI | Internal network | IAM, TLS, least-privilege roles |
| Engine adapters | Process boundary | Contract validation, sandboxed execution |
| Module installation path | Supply chain | Signature + validation + quarantine |
| Receipt store | Local disk/object store | Append-only, hash chain, replication |
| HITL channels (email/UI) | Human | MFA via IAM, challenge expiry |
| External API egress | Internet | Allowlist, request/response hashing |

## 3. Mitigation Strategies (Summary)

- **Defense in depth**: contract layer, verifier layer, brake layer, and
  quarantine layer each independently halt unsafe behavior.
- **Evidence integrity**: receipt/hash-chain mechanisms provide verifiable tamper-evident linkage for the event classes actually captured. They do not, by themselves, prove immutable storage, authenticated authorship, non-repudiation, or complete event coverage.
- **Zero-trust modules**: modules are untrusted until validated; execution
  runs under station policy with brakes armed.
- **Incident response**: runbooks in `governance/runbooks/` (ENT7-R4).

## 4. Compliance Mapping (per SPEC-ENT-002)

| Control | Framework mapping | Residual evidence |
|---|---|---|
| Audit logging | SOC 2 CC7.2, ISO 27001 A.12.4 | Receipt chain, observation records |
| Access control | SOC 2 CC6.1, ISO 27001 A.9 | IAM integration (SPEC-ENT-001) |
| Change management | SOC 2 CC8.1 | CAB-gated pilot + graduation (ENT7-R1) |
| Incident response | ISO 27001 A.16 | Runbooks (ENT7-R4), post-mortems |
| Data protection | GDPR Art. 32 | DPA (ENT8-R8), encryption in transit/at rest |
| Vendor/supply chain | SOC 2 CC9.2 | Module validation, SBOM (SPEC-ENT-005) |

## 5. Vulnerability Scan Evidence Template (per SPEC-ENT-005)

A current release claim requires retained scan reports bound to the exact candidate/artifact, scanner/ruleset identity, configuration, timestamp, and finding disposition. This reference document intentionally carries **no current v1 scan counts**. Historical or example counts MUST NOT be promoted into release evidence without their original exact identity.

## 6. Penetration-Test Evidence Template

A production/commercial security package may require a third-party or scoped penetration test. A current claim must identify the assessor, methodology, tested boundary, exact candidate/artifact, dates, retained report digest, findings, remediation, and retest evidence.

This repository template does **not** claim that a v1 penetration test or retest has been completed, that medium-or-higher findings have been closed, or that a current report is available under NDA.

## 7. Reviewer Sign-off

This file is a reference template for a security review package. It is not suitable as an accepted submission until deployment-specific controls and exact release-bound evidence are populated and reviewed.
Sign-off is recorded as the `security_signoff` graduation criterion in the
pilot framework (ENT7-R1).
