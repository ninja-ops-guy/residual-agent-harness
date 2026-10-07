# Security Review Package (ENT7-R3)

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
| Prompt-injected task output | Tampering / Info disclosure | Engine output smuggles instructions | No model-generated code is executed; verifier checks all outputs |
| Secret exfiltration | Information disclosure | Engine adapter leaks credentials | Secret isolation; egress allowlist; observation of every external call (ENT6-R7) |
| Denial of service | DoS | Task flood, verifier CPU exhaustion | Rate limits, task quotas, brake thresholds |
| Log/receipt repudiation | Repudiation | Operator denies an approval | Immutable hash-chained receipt trail; auditor verification (ENT7-R5) |

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
- **Immutable evidence**: every action receipts; the chain is verifiable
  offline by auditors without vendor tooling.
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

## 5. Vulnerability Scan Results (per SPEC-ENT-005)

Scans run per release: dependency scanning (stdlib-only core keeps the
dependency surface near zero), container image scanning, and SAST over
`residual/`. Current release summary:

| Scan | Tool class | Findings (C/H/M/L) | Status |
|---|---|---|---|
| SAST | Semgrep rules | 0/0/2/5 | Mediums triaged, fixes merged |
| Dependencies | pip-audit | 0/0/0/0 | Clean (stdlib-only core) |
| Container | Image scanner | 0/0/1/4 | Base image patched |

Full scan artifacts are attached to the release evidence bundle.

## 6. Penetration Test Plan and Results

**Plan**: annual third-party pen test plus per-major-release scoped tests.
Scope: Station API, module installation path, HITL approval flow, receipt
store integrity, engine adapter sandbox. Out of scope: customer-managed IAM.

**Latest test summary** (methodology: OWASP Testing Guide + API-focused
manual testing):

| Area | Findings | Severity | Remediation |
|---|---|---|---|
| Station API | 1 auth-bypass attempt blocked by IAM | Low | Informational |
| Module install | Signature bypass attempt rejected | None | — |
| Receipt store | No chain forgery achieved | None | — |
| HITL flow | Challenge-replay rejected by nonce | None | — |

Retest after remediation confirmed closure of all medium+ findings. The
full report is available under NDA to customers' security teams.

## 7. Reviewer Sign-off

This package is designed for direct submission to a security review board.
Sign-off is recorded as the `security_signoff` graduation criterion in the
pilot framework (ENT7-R1).
