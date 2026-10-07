# Data Processing Agreement (DPA) Template — GDPR (ENT8-R8)

Requirement: **ENT8-R8** — Residual MUST provide a Data Processing
Agreement covering controller vs. processor roles, a sub-processor list, a
72-hour data breach notification timeline, and audit rights.

This is the template executed as an annex to the MSA (ENT8-R1).

## Article 1 — Definitions and Roles

- **Data Controller**: the Customer, which determines the purposes and
  means of processing personal data submitted to Residual (task payloads,
  receipts containing personal data, HITL records).
- **Data Processor**: Residual Systems, Inc., processing personal data
  solely on the Controller's documented instructions (GDPR Art. 28).
- Processing subject matter: operation of the Residual platform per the
  agreement; duration: agreement term; nature: storage, execution
  support, receipting; categories: task data, identifiers, logs;
  data subjects: as determined by the Controller.

## Article 2 — Processor Obligations

1. Process personal data only on documented instructions, including for
   transfers (Art. 28(3)(a)).
2. Ensure confidentiality undertakings for all personnel.
3. Implement technical and organizational measures per Art. 32:
   encryption in transit (TLS) and at rest, IAM-based access control
   (SPEC-ENT-001), immutable receipt logging for accountability.
4. Assist the Controller with data-subject requests (access, rectification,
   erasure, portability) within 10 business days.
5. Assist with DPIAs and prior consultations (Arts. 35–36).
6. Delete or return personal data at the end of services, at the
   Controller's choice, within 60 days (receipt-store personal data is
   crypto-shredded via key destruction where hash-chain retention is
   contractually required).

## Article 3 — Sub-Processors

- The Controller authorizes the sub-processors listed in **Annex A**
  (hosting provider, monitoring provider, support tooling).
- New sub-processors: 30 days' advance notice; the Controller may object
  on reasonable data-protection grounds; unresolved objections permit
  termination of affected services.
- Sub-processors are bound by terms no less protective than this DPA;
  the Processor remains fully liable for their acts and omissions.

## Article 4 — Data Breach Notification (72 Hours)

1. The Processor notifies the Controller **without undue delay and no
   later than 72 hours** after becoming aware of a personal data breach
   (supporting the Controller's Art. 33 obligation).
2. Notification includes: nature and categories of data/subjects
   affected, likely consequences, measures taken or proposed, and a
   contact point.
3. The Processor investigates, documents, and cooperates with supervisory
   authority inquiries; incident handling follows the contract-violation
   and station-failure runbooks (ENT7-R4) where applicable.
4. Breach response costs are covered under the cyber liability policy
   (ENT8-R5).

## Article 5 — Audit Rights

1. The Controller may audit Processor compliance once per year (and after
   any breach) with 30 days' notice, using questionnaires, evidence
   bundles (SPEC-ENT-002 compliance reports), and — where insufficient —
   on-site inspection during business hours.
2. Independent third-party auditors may be engaged under NDA.
3. Audit findings: remediation plan within 30 days; critical findings
   within 7 days.
4. Auditor training for receipt-based evidence review is provided per
   the auditor curriculum (ENT7-R5, ENT7-R6).

## Article 6 — International Transfers

Transfers outside the EEA rely on SCCs (Module 2: controller-to-
processor) plus supplementary measures listed in Annex B.

## Annex A — Sub-Processor List (template)

| Sub-processor | Function | Location | Safeguards |
|---|---|---|---|
| [Cloud hosting provider] | Infrastructure | [region] | ISO 27001, SCCs |
| [Monitoring/observability vendor] | Telemetry | [region] | SOC 2, SCCs |
| [Support tooling vendor] | Ticketing | [region] | SOC 2, SCCs |

## Annex B — Supplementary Transfer Measures

Encryption with Processor-held keys, access logging with immutable
receipts, government-access request challenge policy, data minimization
in telemetry.
