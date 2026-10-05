# WEBSITE-LEGAL-001 — bounded publication gate review (2026-10-05)

**Disposition: HOLD — owner approval is not yet evidence-supported.**

This review applies to PR #528 at inspected HEAD `a62d2820fc96c9ad2a1bdb7f9ad6daf9d8dbe4ab`. It is a bounded publication review, not a legal-compliance certification, legal opinion, v1 release acceptance, or permission to bypass `LEGAL_PUBLICATION_HOLD` / `V1_RELEASE_HOLD`.

## Verified at this head

- `site/legal/publication.json` names operator **Mike Olivares** and public privacy contact **mikeskinddread@gmail.com**.
- `runtime_disclosure` and `international_processing` are populated and expressly preserve uncertainty around provider-controlled handling, transfer agreements, and live served-asset inventories.
- `effective_date` remains `null`; `owner_review_complete` remains `false`.
- GitHub Actions exact-head results show success for RESIDUAL Qualification v1, Command Station, controller/provider contracts, Control Plane, clean install, measured-evaluation binding, Factory ownership, Browser VM Demo CI, and iOS WebKit preflight.
- Pages run `37304345909` fails at the intentional legal publication gate. This is the expected fail-closed behavior while owner review is incomplete.
- Maintainer approval and PR-Agent advisory review are separate gates and remain outside this publication decision.

## Active deployment inventory finding

The repository is linked to Vercel project `prj_ng8IyUVOadX7h7lbH2d6toRuT0St` (`residual-agent-harness`) under team `team_9I7KMEV5zHoRMK3omb4Meg0A`.

Observed project state during this review:

- Vercel project framework: Python.
- Project reports `live: false`.
- SSO protection is enabled for `all_except_custom_domains`; password protection is disabled.
- The single listed project domain is `residual-agent-harness.vercel.app`.
- No project routing rules were returned.
- Exact PR-head deployment `dpl_THYvLoZchSXzNaVznPDsuAZXMwcS` is READY and is bound to commit `a62d2820fc96c9ad2a1bdb7f9ad6daf9d8dbe4ab`.
- Fetching the PR preview root and `/legal/privacy.html` returned HTTP 404 JSON (`{"error":"not found"}`) with `no-store`, `x-robots-tag: noindex`, HSTS, CSP `default-src 'none'; frame-ancestors 'none'`, `X-Frame-Options: DENY`, and restrictive permissions policy.

**Disposition:** this Vercel preview is a real deployment surface but was not observed serving the public Pages website or legal pages. Do not describe the Pages legal hold as blocking every deployment. The preview should remain separately inventoried; if it is not intended as a public website, preserve/review its access controls and avoid marketing it as the legal-notice-bearing surface.

## Mailbox validation

The selected Gmail address is configured in the candidate, but this review did **not** obtain evidence of an inbound privacy-request test message or a documented private rights-request workflow. A connected-mailbox search did not yield a recent message addressed to `mikeskinddread@gmail.com` that could be used as receipt evidence.

**Disposition: HOLD.** The address selection is verified; operational receipt/monitoring is not.

## Items that remain UNKNOWN / external

The following are intentionally not closed by repository text alone:

- Provider agreements / DPAs, account-specific retention, model-training terms, processing roles, and transfer mechanisms for flows where those requirements apply.
- Exact live runtime CDN/request inventory and retention/logging behavior for every WebVM/CheerpX/Puter/upstream-model route.
- Third-party license/developer-agreement obligations beyond repository-visible notices, including any employment/IP or contributor-rights issue not evidenced in the repository.
- Full assistive-technology testing and any legal accessibility conclusion.
- Jurisdiction-specific counsel conclusions, business registration/address/representative obligations, or a blanket GDPR/CCPA/CTDPA/ADA/COPPA certification.

## Owner-approval condition

Do **not** set `effective_date` or `owner_review_complete: true` yet.

Owner approval becomes supportable only after:

1. A real inbound message to the published privacy mailbox is received and the private handling/reply process is recorded.
2. The Vercel preview is explicitly dispositioned as either an intentionally protected/non-site deployment or brought under the legal publication surface; its behavior must not contradict the published inventory.
3. Any provider/licensing/transfer item required for the intended initial public launch is either evidenced, expressly scoped out, or left as a documented external/counsel HOLD.
4. The owner reads the rendered notices and accepts the remaining bounded scope.

After those conditions are met, set the **actual publication date** (not a backdated review date), set `owner_review_complete: true`, then rerun exact-head Pages, rendered browser checks, provider qualification, and the existing independent/release gates. Evidence must bind to the new exact HEAD.

## Current gate result

`LEGAL_PUBLICATION_HOLD = PRESERVE`

Reason: mailbox operations are unverified and the separate Vercel deployment surface has been inventoried but not fully dispositioned. No evidence supports declaring blanket legal compliance.
