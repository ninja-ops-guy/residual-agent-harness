# Commercial Entity (ENT8-R1)

Requirement: **ENT8-R1** — a commercial entity MUST exist behind Residual,
able to sign contracts, accept payment, provide invoices, and be liable for
breaches.

## Entity Structure

**Residual Systems, Inc.** — a Delaware C-corporation — is the commercial
entity behind the Residual platform. The open-source core remains
permissively licensed; the corporation holds the commercial trademarks,
enterprise feature IP, and all customer contracts.

## Capabilities

| Capability | Mechanism |
|---|---|
| Sign contracts | Authorized officers execute MSAs, order forms, DPAs (ENT8-R8), and support agreements (ENT8-R2) under Delaware law |
| Accept payment | Wire/ACH (net-30), credit card for self-serve tiers; USD, EUR, GBP invoicing |
| Provide invoices | Itemized invoices per order form: license line items by metering model (ENT8-R7), support tier, professional services (ENT8-R3) |
| Liability | Contractual liability accepted per MSA; backed by insurance program (ENT8-R5); indemnification obligations (ENT8-R4) are binding on the corporation |

## Contracting Stack

1. **Master Services Agreement (MSA)** — umbrella terms, liability caps,
   indemnification.
2. **Order Form** — license tier, metering model, quantities, price.
3. **Support Addendum** — tier and SLAs (ENT8-R2 / support-tiers.md).
4. **DPA** — GDPR data processing terms (ENT8-R8 / dpa.md).
5. **Professional Services SOW** — per engagement (ENT8-R3).

## Procurement Support

- W-9 (US) / Certificate of Incorporation available on request.
- Vendor onboarding: standard procurement portals supported (Coupa,
  Ariba, SAP Fieldglass).
- Insurance certificates per ENT8-R5; financial stability evidence per
  ENT8-R6 (financial-stability.md), both deliverable during due diligence.
