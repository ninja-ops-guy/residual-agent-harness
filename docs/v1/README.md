# RESIDUAL v1 claim control

This directory is the machine-readable authority layer for public v1 claims.

Controlling rule:

> Qualification does not confer admission. Admission does not confer support. Support does not exist until the corresponding admitted and qualified capability is included in an authorized release.

`CLAIM_REGISTRY.json` controls capability state. Experimental evidence may exist for a non-admitted capability, but only `ADMITTED_D3` capabilities may become D3/RC-qualified. `SUPPORTED` is prohibited until the capability is part of an authorized release.

`DOCUMENT_AUTHORITY.json` classifies documents as current normative/descriptive, historical evidence, proposals, reference templates, or roadmap material. Only current normative material may be marked eligible to satisfy a current release-evidence requirement.

`AUDIT_BASELINE_D796F36.json` preserves the contradiction-audit identity and current-main reproduction status. Baseline findings are never silently deleted; they move through PENDING_REPRODUCTION, STILL_PRESENT, PARTIALLY_RESOLVED, SUPERSEDED, or NEW_FORM.

This control plane narrows claims. It MUST NOT expand D3 or require enterprise implementation merely to make public prose true.
