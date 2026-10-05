# WEBSITE-LEGAL-001: international-processing source review

Review date: **2026-10-05**. Status: **DRAFT NOTICE / INDEPENDENT REVIEW REQUIRED**.

This supplements [WEBSITE_COMPLIANCE_REVIEW.md](WEBSITE_COMPLIANCE_REVIEW.md).
It is source-based drafting evidence, not a legal opinion, a completed transfer
assessment, an independent verification, or a public-deployment acceptance.
`LEGAL_PUBLICATION_HOLD` and `V1_RELEASE_HOLD` remain unchanged.

## Candidate and authorization boundary

The inspected PR #528 head before this pass was
`e8a0607754787bfc82547a24698dc827768e8557`, on
`feat/site-privacy-legal-001`. The owner approved drafting and committing the
international-processing section while retaining an unset effective date and
`owner_review_complete: false`. The previously selected public contact remains
`mikeskinddread@gmail.com`. Selecting the address is not proof of tested mail
delivery, mailbox monitoring, or a completed privacy-request process.

This pass changes policy configuration and documentation only. It does not
change consent controls, provider grants, Station authority, release gates,
workflow permissions, or the deployed Pages branch.

Implemented commits before this review note:

- `6e170a6e631848428b793e47f8705d0154dc83fa`: populated the international-processing
  draft and corrected two source-based retention/diagnostic descriptions.
- `4cfa651c2f8aff5c65105436dd3b1732dc4a7f83`: identified Gmail correspondence and
  added a dedicated international-processing heading with provider-source links.

## Provider facts and their limits

The following public sources were read on the review date. A provider policy
supports an attributed statement about that provider; it does not prove the
contract, actual region, account settings, or processing role for every RESIDUAL
flow. A policy link is not evidence of a signed agreement.

| Flow | Supported disclosure | What is not established |
| --- | --- | --- |
| GitHub website delivery | GitHub describes processing in the United States and other operating locations, and its own reliance on European Commission Standard Contractual Clauses for some international transfers. | A fixed Pages data-residency region, or a RESIDUAL-specific signed agreement covering all flows. |
| Optional Puter access and AI requests | Puter describes possible handling in Canada and other countries. Model-request recipients depend on the selected upstream service. | A complete model-routing country list, model-specific retention/training commitments, or a particular transfer safeguard for every route. |
| Privacy/support correspondence | The owner-selected Gmail address introduces Google email processing. Google's policy describes geographically distributed servers and possible processing outside a person's country. | Google Workspace enterprise terms, a particular mailbox region, or account-specific retention/forwarding controls. No private email or account settings were inspected. |
| WebVM/CheerpX runtime delivery | The pinned WebVM source imports `@leaningtech/cheerpx`; vendor documentation describes client-side execution and runtime distribution. Runtime delivery must be distinguished from local guest execution. | Exact served CDN hosts, all delivery regions, runtime logging retention, and safeguards for every delivery service. The vendor's general website policy is not a CDN-specific attestation. |

Sources and relevant sections:

1. GitHub General Privacy Statement, **International data transfers**:
   https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement#international-data-transfers
2. Puter Privacy Policy, **5. Cross-Border Data Transfers**, with its existing
   published effective date of 2022-07-18 (checked in 2026, not rewritten as a
   2026 policy): https://puter.com/privacy
3. Google Privacy Policy, **Data transfers** and its discussion of communication
   information: https://policies.google.com/privacy
4. Leaning Technologies website policy, **3. What Does This Policy Cover?** and
   **8. How and Where Do You Store My Data?**:
   https://leaningtech.com/privacy-policy/
5. CheerpX vendor description of client-side execution and delivery options:
   https://labs.leaningtech.com/blog/cx-10
6. Pinned upstream WebVM source (not a live network capture):
   https://github.com/leaningtech/webvm/blob/388d0adeb319d9ad605a5ec0485777cff5430c88/src/lib/WebVM.svelte

The Leaning Technologies website policy limits its scope to its own site. Its
UK-storage wording must not be reused as a promise that all CheerpX runtime/CDN
requests or customer deployments stay in the UK. Likewise, do not import the
privacy or regional terms of BrowserPod or CheerpJ into this different product.

## Legal mechanism is separate from feature authorization

The draft deliberately does not claim that browsing, choosing to load Puter,
or authorizing a prompt waives international-transfer requirements. It also does
not declare RESIDUAL compliant merely because GitHub or Google describes its own
safeguards. No Data Privacy Framework certification is asserted for RESIDUAL.

Where the relevant transfer rules apply, determine the sender/recipient roles,
territorial scope, data categories, destinations and applicable mechanism for
that specific flow. The current ICO guidance distinguishes adequacy, appropriate
safeguards, and narrowly applicable exceptions. Its guidance also explains that
relying on contractual safeguards can require an assessment, additional measures
and legally binding execution; exceptions must be justified rather than assumed.

Primary regulatory sources checked on 2026-10-05:

- ICO, **How do we comply with the transfer rules if we are initiating the
  restricted transfer?**
  https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/a-guide-to-international-transfers/how-do-we-comply-with-the-transfer-rules-if-were-initiating-the-restricted-transfer/
- ICO, **What are the exceptions?**, especially the precise information needed
  for explicit transfer consent:
  https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/using-an-exception/what-are-the-exceptions/

These are review criteria, not a determination that UK law applies to every
visitor or that the UK mechanism resolves EU or other jurisdictions' rules.
Keep the applicable-jurisdiction and agreement review from the main checklist.

## Corrections to the previous runtime wording

### Conversation index is not a deletion limit

At inspected source `e8a0607`, `demo/vm/mission-control-world.js` uses
`residual.chat.current.v2`, `residual.chat.index.v2`, and separate
`residual.chat.session.v2.<id>` entries. `index()` and `save()` limit the visible
index to eight entries. `load()` and `append()` limit retained/restored turns to
sixteen. `save()` does not delete conversation records evicted from the index,
and the inspected code has no time-based expiry for those records.

The notice now distinguishes the index limit from physical retention. It does
not promise that only eight conversations remain in localStorage. Whether
persistent transcript storage needs additional opt-in, expiry or deletion
controls for the intended audience remains an acceptance review item. This
wording correction does not implement those controls.

### Diagnostic size is not a guaranteed byte cap

At the same source, `demo/vm/mission-control-diagnostics.js` compares
`text.length` against `MAX_PERSIST_BYTES` while trimming serialized events.
JavaScript string length is not a UTF-8 byte count. The notice no longer describes
this as a guaranteed 1 MiB cap. It also warns that pattern-based redaction does
not guarantee anonymity. No diagnostic-buffer implementation was changed.

## Independent review handoff and done condition

Review the exact successor head of PR #528; do not transfer approvals from an
older tree. Confirm the final changed-file list and source identity first.

1. Compare the rendered privacy and storage notices against the actual built
   Pages artifact. Preserve the selected contact address; verify incoming mail
   and a private reply process without publishing message contents.
2. Capture first-visit, walkthrough, VM, provider-load, sign-in, inference,
   withdrawal, reload and storage-blocked behavior. Record recipient origins and
   storage names/purposes without leaking tokens, prompts or personal data into
   public evidence. Use synthetic content for tests; any real paid-provider
   exercise requires explicit owner authorization and an appropriate account.
3. Complete the runtime-delivery and upstream-model inventory. The pinned
   upstream `src/app.html` also contains Google Fonts preconnect hints; inspect
   the final artifact and transitive dependencies rather than assuming that
   removal of Plausible makes the entire dependency chain tracker-free.
4. Resolve applicable jurisdictions, actual agreements/roles, mailbox retention,
   rights handling, and any necessary transfer mechanisms. Obtain qualified
   legal review as appropriate. Do not set a review boolean in lieu of evidence.
5. Run the existing publication, privacy-control and real Pages/browser checks
   from the main checklist on the final candidate. Inspect accessible links,
   actual text, optional-provider boundaries and storage deletion behavior.
   Correct failures before proposing publication.
6. After those reviews and explicit owner approval, set the intended initial
   publication date, set the reviewed configuration approval, and obtain the
   exact-head qualification. Merge/deploy only through the existing release
   process, then verify the served commit, notices and links. Correct the date
   before publication if the release schedule changes.

**Done means:** an independently reviewed, actually served notice that matches
its deployment, with the applicable operational/legal requirements resolved.
A non-null international-processing field alone is not this done condition.

## Other deployment boundary

PR #528's Vercel bot comment `5987973808` reported a preview deployment as Ready
on 2026-10-05. That comment was observed, but the preview's accessibility, served
content and data flows were not inspected in this pass. It is not evidence that
the Pages legal notices are live. Conversely, a Pages publication hold must not
be described as a global block on Vercel previews or on reading source templates.
Inventory or restrict any other publicly reachable deployment separately before
making a whole-website compliance claim. Do not disable or change deployments
without the appropriate owner authorization.

## Verification performed in this pass

- Read the current PR metadata, configuration, privacy template, publisher guard,
  relevant client source and provider policies through the available connectors
  and web sources.
- Executed local JSON assertions for schema/key preservation, the selected email,
  populated disclosure strings, absence of unfinished transfer placeholders,
  `effective_date: null`, and `owner_review_complete: false`.
- Independently calculated the updated configuration's Git blob SHA as
  `7a642eef5a37add46b99319400ce684a63c3b242`; GitHub returned the same content SHA.
- A full repository clone was attempted but failed because this container could
  not resolve `github.com`. No existing full suite or live/browser/provider test
  was rerun. Earlier reported test results remain historical and are not promoted
  to this successor candidate.

No new legal approval, mailbox-delivery proof, live network inventory, real
provider authentication/inference, accessibility certification, full CI PASS,
production deployment or v1 release acceptance is claimed.
