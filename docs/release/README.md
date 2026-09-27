# RESIDUAL v1 Release Preparation

**Status:** PREPARATION MATERIAL — not release authority.

This directory contains reviewer-facing material for moving one exact, feature-frozen candidate through qualification, RC selection, soak, and release.

## Documents

- `V1_RELEASE_RUNBOOK.md` — serial release process and stop conditions.
- `V1_SUPPORT_MATRIX.md` — intended v1 support surface and explicit deferrals.
- `V1_EVIDENCE_INDEX.md` — exact-candidate evidence routing template.
- `V1_RC_CHECKLIST.md` — detailed owner/reviewer checklist from candidate freeze through publication.
- `V1_RELEASE_CHECKLIST.md` — compact release-gate checklist.
- `V1_RC_SOAK_POLICY.md` — required 24h release soak, extended 72h tier, identity and reset semantics.
- `V1_RELEASE_NOTES_TEMPLATE.md` — evidence-bound v1.0.0 release-notes skeleton.
- `V1_KNOWN_LIMITATIONS_TEMPLATE.md` — release-note non-claims and limitations template.
- `V1_QUALIFICATION_HANDOFF_TEMPLATE.md` — one-page handoff from feature freeze into Q1/Q2/Q3/Q4.
- `STABILIZATION_2026-09-17.md` — historical stabilization context; not current release authority unless independently rebound to the final candidate.

## Authority rule

A document in this directory never upgrades historical evidence into exact-candidate evidence. Release claims require receipts bound to the exact product HEAD/TREE and, where applicable, exact promoted artifact digest.

The human owner retains authority for product/helper freeze, physical F6 authorization, RC selection, and release publication.

## Freeze rule

After a proposed v1 tree is declared feature-frozen, no source change enters that candidate unless a mandatory qualification gate demonstrates a defect and the owner authorizes a successor. The failed predecessor remains immutable historical evidence.

