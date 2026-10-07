# Licensing Policy (ENT8-R7)

> **License-scope note:** This document describes product-tier behavior and commercial intent; it is not itself a license grant. The actual Apache-2.0 scope is defined by [../../../LICENSING.md](../../../LICENSING.md) and [../../open-source/OPEN_SOURCE_MANIFEST.md](../../open-source/OPEN_SOURCE_MANIFEST.md). Enterprise implementations remain reserved unless explicitly added to that manifest.

Requirement: **ENT8-R7** — Residual MUST offer flexible licensing: open
source (core platform), commercial (enterprise features), per-node /
per-task / flat-rate pricing, and educational and non-profit discounts.

Implemented in code: `residual/licensing/model.py` (`License`, `Tier`,
`MeteringModel`, `UsageMeter`) with enforcement hooks (`License.require`,
node/task limit enforcement in `UsageMeter`).

## 1. Editions

### Open Source (Tier.OPEN)
- Core platform: task execution, HITL, brakes, receipts, modules
  (`OPEN_FEATURES`).
- Community/open-core features are distributed only when explicitly listed in the Open Source Manifest; community support only.

### Commercial (Tier.COMMERCIAL)
Enterprise features (`COMMERCIAL_FEATURES`):
- **Multi-tenancy** (`multi_tenancy`)
- **HA/DR** (`ha_dr`) — standby stations, receipt replication
- **Compliance reporting** (`compliance_reporting`, SPEC-ENT-002)
- **Premium support** eligibility (`premium_support`, ENT8-R2)
- **SSO/SCIM** (`sso_scim`) and **audit export** (`audit_export`)

Enforcement: calling an enterprise feature without a commercial license
raises `ContractError` from `License.require(feature)`.

## 2. Metering Models (`MeteringModel`)

| Model | Unit | List price | Enforced by |
|---|---|---|---|
| `per_node` | Station node / month | $1,200 | `UsageMeter.register_node` rejects beyond `node_limit` |
| `per_task` | Executed task | $0.05 | `UsageMeter.record_task` rejects beyond `task_limit` |
| `flat` | Year | $60,000 | No usage caps |

Flat-rate licenses carry no node/task caps (`node_limit = task_limit = 0`).
Overage reports (`UsageMeter.overage()`) feed billing reconciliation and
true-up at renewal.

## 3. Discounts

| Tier | Discount off list |
|---|---|
| Educational (accredited institutions) | 50% |
| Non-profit (registered charities) | 40% |

Discounts are applied in `License.price()`; eligibility verified during
order processing.

## 4. License Terms Highlights

- Licenses are subscription (1- or 3-year); perpetual fallback for the
  open core only.
- Pilot programs (ENT7-R1) run on time-boxed commercial trial licenses
  with full enterprise features.
- Audit: customers self-report usage via `UsageMeter` exports; vendor
  audit right once per year with 30 days' notice.
- License keys identify `licensee`, `tier`, `metering`, and limits;
  tampering is detectable (identifier validation, `ContractError`).

## 5. Upgrade / Downgrade

- Open → Commercial: in-place; no data migration (receipt store format
  is shared).
- Commercial → Open at term end: enterprise features deactivate via
  enforcement hooks; core operation and all receipts remain accessible.
