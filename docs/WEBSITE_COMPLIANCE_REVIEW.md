# WEBSITE-LEGAL-001 — public Pages privacy and legal review

**Status: IMPLEMENTATION CANDIDATE; LEGAL_PUBLICATION_HOLD.** Requested by the
owner on 2026-10-04. This is not an assertion of legal compliance or a v1 release
acceptance. Preserve V1_RELEASE_HOLD and all existing merge/qualification gates.

## Scope and baseline

Inspected main: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`, tree
`7cd0d32be6fd61948f2fce753b122e5b6f0c6500`. Public Pages root is
`https://ninja-ops-guy.github.io/residual-agent-harness/`. Covers homepage,
walkthrough, browser VM, and provider panel. It does not approve a Vercel gateway,
self-hosted deployment, production account service, private swarm, or future
commercial platform. Public-site fetches could not be completed in the authoring
environment; this is not evidence of an outage.

Existing evidence: `.github/workflows/pages.yml` builds `_site`; `provider.js`
loads Puter on a separate user click and bounds per-mission grants; Mission
Control has per-run consent; the walkthrough formerly stored progress without a
separate remember choice. `SECURITY.md` and `LICENSING.md` already distinguish
bounded claims, private vulnerability reporting, mixed-scope licenses, and
unresolved ownership questions. This candidate does not change source licenses.

## What this candidate changes

* `site/legal/`: privacy, storage/choices, terms/licenses, accessibility/contact,
  local CSS, precise walkthrough deletion, and visible legal links in the
  Mission Control flex layout. No remote font or analytics dependency is added.
* `site/walkthrough-persist.js`: off-by-default remembering, 180-day expiry,
  no restoration of legacy progress without consent, withdrawal across tabs,
  and an in-memory fallback when storage is unavailable. Only the two named
  walkthrough keys are removed. Reset is not VM erasure.
* `demo/vm/provider.html`: point-of-collection disclosures, explicit, feature-led provider
  load choice, withdrawal, external policies, cost and sensitive-data warnings.
  The existing `referrer=origin` sign-in fix is preserved.
* `demo/vm/publish_legal.py`: review-gated rendering, static links on all four
  active routes, required import and entry guard in the **generated** provider
  module, and a source-bound artifact manifest. Patch-anchor drift fails closed.
  The existing Load button is the explicit choice (no new checkbox step is
  imposed on established browser acceptance flows). Programmatic loads without
  a fresh user click fail closed. Provider loading remains distinct from
  authentication and per-run
  authorization. Withdrawal unloads the panel, not already-submitted requests.
* `pages_contract.py`: calls the publisher before recording final index hashes.
  No workflow permissions, acceptance rules, release gates, or Station authority
  change. The normal Pages build deliberately fails until the owner inputs below
  are supplied; do not merge a failing build as a temporary workaround.

The source provider HTML is a build input. The mandatory guard is installed in
its generated JavaScript by the Pages publisher. Do not host `demo/vm/` directly
or copy templates verbatim. The qualifying artifact is `_site`, not a source
file viewed alone. The publisher does not certify provider software or run an
independent whole-site privacy scan.

## Owner decisions required before publication

Edit `site/legal/publication.json` only after these facts are resolved. It is not
an attestation API: changing a boolean is not evidence of review.

1. Confirm the actual website operator/controller and a **working, monitored
   public privacy contact email**. Do not invent an LLC, inbox, representative,
   physical address, or DPO. Validate incoming mail and a private reply process.
   Review whether applicable trading/entity laws require additional business
   address, registration, tax, or representative disclosures.
2. Complete `runtime_disclosure` from the exact deployed network/storage
   inventory. Identify GitHub hosting, WebVM/CheerpX runtime origins, cookies,
   IndexedDB/cache purposes and retention; test first visit, replay, VM opening,
   provider load, sign-in, request, cancellation, and withdrawal. Investigate
   conversation persistence too: current browser tests reference
   `residual.chat.current.v2`; do not equate closing a tab with deletion. Include both
   normal and narrow browsers and storage-blocked behavior. An absent analytics
   script in one HTML file is not proof that every dependency is tracker-free.
   Check all active domains/deployments, not just this Pages branch.
3. Complete `international_processing` with actual locations, roles, and legally
   applicable safeguards, how to obtain their details, and any representative
   contact required. Determine whether EU/UK targeting or monitoring brings those
   laws into scope. Do not describe ordinary browsing/provider consent as a
   substitute for a required transfer mechanism. Obtain the relevant provider
   agreements/DPAs and review model retention/training terms where necessary.
4. Review the privacy text against real support-email practices, retention,
   deletion, rights verification, appeals and incidents. Record an owner and
   evidence for each. Verify third-party license conditions (particularly
   WebVM/CheerpX and Puter developer use), notices, contributor rights, historical
   licensing and employment/IP obligations before commercial distribution.
5. Review legal applicability, exact notices, marketing claims and accessibility
   with qualified counsel as appropriate; set the real effective date and
   `owner_review_complete: true` only after approval. This authoring pass does not
   make blanket GDPR, CCPA/CPRA, CTDPA, COPPA, ADA, SOC 2, or HIPAA claims.

## Acceptance evidence, not just policy text

Run `python -m unittest discover -s tests -p test_webvm_legal.py -v`,
`node --test tests/web-privacy.test.mjs`, and
`python tests/web_privacy_browser.py` (Playwright + Chromium) for local fixtures.
The fixture contact, review status, runtime, and transfer text are synthetic and
must NEVER be copied into production configuration. Browser tests use a stub
provider and minimal walkthrough; they do not establish real provider sign-in
or full guest compatibility.

After owner review, run the existing exact-head provider/workbench/publication
suites and complete Pages desktop + narrow WebVM qualification. On the actual
qualified artifact, verify:

- All privacy/terms/choices/contact links are visible, keyboard reachable and
  correct under the project subpath, including full-screen Mission Control and
  provider setup. Read all rendered pages; no missing fields or promises beyond
  the observed behavior. Added pages work at narrow widths and 200–400% zoom.
- No provider requests, sign-in, or SDK code execute before the load choice;
  per-run authorization remains mandatory. Withdrawal unloads the SDK,
  blocks future requests and does not claim cancellation of dispatched calls.
  Test reload/BFCache and an existing provider session.
- Walkthrough browsing produces no optional progress write before opt-in;
  expiry, cross-tab withdrawal, reset, blocked storage, and old-key migration
  work. Forget removes only the documented two keys. GPC/DNT disclosures match
  behavior; no optional sale/ad function is silently enabled.
- Record the final source commit, legal/build-manifest.json, demo/build-info.json,
  test logs, request/cookie/storage inventory, accessibility results and the
  independent reviewer. Re-run after reconciliation, merge, and deployment;
  evidence does not transfer across different candidate trees.

The CSS/CSP in these pages is not a substitute for secure hosting headers.
`frame-ancestors` is not enforced from a meta CSP; review actual response headers,
HTTPS, script supply chain, storage isolation, and incident response separately.
A positive automated accessibility test is not a full assistive-technology audit.

## Applicability and operations ledger

* **Privacy notice:** CalOPPA can apply to commercial websites collecting covered
  information about California consumers without the larger CCPA business
  thresholds. Check actual applicability rather than assuming a small project is
  exempt. Categories, recipients, changes, effective date and tracking signals
  are covered in the candidate notice.
* **Connecticut:** use the current AG guidance; do not reuse an old 100,000-user
  threshold. Sensitive data and offering data for sale can change applicability.
  Apply required opt-out signals, rights, appeals, security/minimization and
  impact assessments when in scope. A no-sales configuration is not an exemption
  from every privacy obligation. Maintain a private request log and deadline
  process (CT generally 45-day response and 60-day appeal response where required).
* **EU/UK:** document territorial scope, controller/processor roles, purposes and
  bases, recipients, retention, rights, transfers, and any representatives.
  ICO storage/access rules include localStorage and scripts, with current
  exceptions; this implementation uses granular feature-led choices rather than
  claiming every nonessential technology always requires a banner.
* **Children/accessibility:** a general-audience label does not defeat actual
  child-directed use or knowledge obligations. A statement does not fix an
  inaccessible interface. Assess audiences, actual behavior and applicable laws.
* **New scope:** accounts, analytics, uploads, research participant collection,
  newsletters, payments, subscriptions, customer hosting, new model services or
  geographic targeting trigger a fresh assessment before activation. Add only
  applicable processor contracts, notices at collection, cookie controls, consumer
  purchase/cancellation disclosures, marketing-consent/unsubscribe handling,
  research consent or other requirements. Do not publish inapplicable promises.

## Primary sources reviewed 2026-10-04

- California BPC 22575:
  https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=22575.
- Connecticut AG current CTDPA guidance:
  https://portal.ct.gov/ag/sections/privacy/the-connecticut-data-privacy-act
- ICO storage/access guidance, updated 29 April 2026:
  https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/
- GDPR, particularly Articles 3, 12–14, 44–49:
  https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng
- DOJ accessibility guidance:
  https://www.ada.gov/resources/web-guidance/
- FTC children's privacy:
  https://www.ftc.gov/business-guidance/privacy-security/childrens-privacy
- GitHub Pages security logging:
  https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- GitHub privacy:
  https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement
- Puter privacy and terms (do not imply these replace a required developer agreement):
  https://puter.com/privacy
  https://puter.com/terms

## Implementation checks recorded in the authoring environment

- 13/13 Python publication/unit checks passed.
- 10/10 JavaScript control-logic checks passed using explicit DOM/storage stubs.
- The existing pages_contract.py base was reconstructed and its Git blob SHA
  verified as `c023c12d33bf71246c9255432821a2453776e782` before the small hook patch.
- Chromium launched, but navigation to the local fixture server failed with
  `net::ERR_BLOCKED_BY_ADMINISTRATOR`. No rendered-browser, real-provider,
  assistive-technology, whole-guest, CI, or live-deployment PASS is claimed.
- Full repository checkout could not be obtained in this environment; the existing
  whole-repository tests were not run. The candidate's source and tests are
  supplied for exact-head CI and independent review.

These are author-executed bounded checks, not independent acceptance evidence.
The production configuration remains intentionally unapproved and incomplete.
