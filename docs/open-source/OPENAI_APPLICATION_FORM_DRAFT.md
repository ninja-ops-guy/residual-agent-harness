# OpenAI application form draft

**Status:** Public-safe draft only — not submitted and not an acceptance of program terms  
**Verified against official forms:** 2026-11-22 (public field text and terms; browser-enforced limits not independently inspected)  
**Maintainer:** Mike Olivares (`ninja-ops-guy`)

This file maps public-safe application answers to the current OpenAI Codex Open Source Fund and Codex for Open Source forms. Private account information must be entered directly by the maintainer and must not be committed to this repository.

Official forms and program information:

- Codex Open Source Fund: <https://openai.com/form/codex-open-source-fund/>
- Codex for Open Source: <https://openai.com/form/codex-for-oss/>
- Program overview: <https://developers.openai.com/community/codex-for-oss>
- Program terms: <https://developers.openai.com/codex/codex-for-oss-terms>

The maintainer must re-check the official pages immediately before submitting because fields, eligibility, benefits and terms may change.

## Private fields — complete only in the official form

Do not add these values to this public file:

- email associated with the maintainer's ChatGPT account;
- LinkedIn URL, if supplied;
- OpenAI Organization ID; and
- any verification or account-recovery information.

## Shared identity fields

**First name**  
Mike

**Last name**  
Olivares

**Personal GitHub / username**  
`ninja-ops-guy`

**Public repository**  
<https://github.com/ninja-ops-guy/residual-agent-harness>

## Codex Open Source Fund

### Which open source project are you representing?

RESIDUAL Open Core

### Brief description of the project

RESIDUAL is an early-stage evidence-first verification and research project for AI-assisted engineering. Its proposed Open Core is a narrowly scoped kernel. It separates model or worker proposals from maintainer-controlled acceptance, retains evidence and receipts, and checks bounded outputs against explicit verifier contracts before integration. The manifest-scoped candidate Apache-2.0 layer exposes provider abstraction, observation, verification, evidence and policy primitives. Factory, runtime orchestration, Studio, enterprise, control-plane and hosted-service implementation remain reserved.

### Other people working on the project and their roles

Mike Olivares — creator, primary maintainer, research lead and final release/integration authority. Other human contributors and their roles must be confirmed before submission. Automated agents are tooling, not human collaborators or benefit recipients.

This answer must be updated if another person will actually perform grant-funded work or receive a program benefit.

### How would you use API credits for your project?

Use OpenAI API credits with Codex and OpenAI models for issue and pull-request review assistance, documentation, regression and malformed-output testing, and reproducible evaluations of the manifest-listed Open Core. Publish revision-bound evaluation methods, positive and negative results, and maintenance improvements. Keep separate usage records and a spending cap. Credits would not pay other providers, hardware, salaries, or reserved Factory, runtime, Studio, enterprise, control-plane or hosted-service implementation. Broader model-comparison research would proceed only within the approved award scope; this request does not assume every research workload is eligible.

### Is there anything else you would like OpenAI to know?

I am the creator and primary maintainer. RESIDUAL is early-stage; broad adoption and independent assurance are not established. The repository is mixed-scope, and the manifest-listed Apache-2.0 Open Core remains a candidate pending maintainer acceptance. At commit c13fc3b9, Open Core Boundary run #170 passed its exporter, boundary, static import and isolated smoke gates; several other workflows failed and maintainer approval is pending. This does not establish production fitness, ownership clearance or program eligibility. The application text is public-safe; repository provenance and rights remain for maintainer/legal review.

## Codex for Open Source

### Maintainer role

Select: **Primary maintainer**

Role description:

I created RESIDUAL and serve as its primary maintainer, research lead and final integration/release authority. I administer the public repository, review changes and evidence, maintain the open/reserved boundary, and retain authority over accepted revisions. Automated qualification supports review but does not replace human maintainer approval.

### Why does this repository qualify? — maximum 500 characters

RESIDUAL is an early-stage verification and research project for AI-assisted engineering. Its proposed Open Core contains manifest-scoped provider, observation, evidence and verification primitives. Potential ecosystem value is reproducible checks of model-generated work; broad adoption and independent assurance are not established. The public monorepo also contains reserved implementation, and the candidate Apache-2.0 scope requires maintainer acceptance.

**Character count:** 460

### Benefits of interest

Proposed only; no selection has been made:

- **API credits for my project**
- **Codex Security** — defer until the exact scan scope and any reserved-code access are approved.

Codex Security use must remain limited to repositories, systems and code the maintainer owns, maintains or is authorized to review.

### How will you use API credits? — maximum 500 characters

Use OpenAI API credits with Codex and OpenAI models for issue/PR review assistance, regression and malformed-output tests, documentation, and reproducible evaluations of the manifest-listed Open Core. Publish revision-bound methods and positive and negative results. Track usage separately from reserved product development; do not spend these credits on proprietary implementation or other providers. Broader research use remains subject to award terms.

**Character count:** 454

### Anything else we should know? — maximum 500 characters

I am RESIDUAL's creator and primary maintainer. At c13fc3b9, Open Core Boundary run #170 passed 16 exporter fixtures, boundary validation, static import closure and isolated archive smoke tests. Other workflows failed; maintainer acceptance and provenance review are pending. This is a candidate export, not a certified release, ownership audit or broad CI pass. The request covers only the manifest-listed Open Core.

**Character count:** 417

## Terms and submission review

Before submitting, the maintainer should confirm all of the following against the then-current official terms:

- application information is accurate and complete;
- repository affiliation and control can be verified;
- benefits may be personal, limited, non-transferable and have no cash value;
- API credits and Codex Security may require separate review or additional terms;
- security review is limited to owned or authorized repositories/systems;
- application materials contain no confidential information;
- OpenAI assumes no exclusivity and may work with similar or identical projects;
- program benefits, eligibility and terms may change; continued participation after a terms update constitutes acceptance;
- recipients are responsible for applicable taxes, reporting and local requirements; and
- submission does not expand RESIDUAL's license boundary, assign reserved IP or authorize activity outside the maintainer's rights.

## Final submission gates

- [ ] The final PR head has passed the exact-head Open Core boundary workflow. Run #170 passed at `c13fc3b9a7fe85142fcfebece839bb2f290cf6ff`; any subsequent documentation edit requires a new run for the new head.
- [ ] The maintainer has reviewed the final repository diff and retained evidence.
- [ ] Private fields have been entered directly in the official form.
- [ ] Current form fields and terms have been re-verified.
- [ ] All application claims remain supported and appropriately limited.
- [ ] The maintainer explicitly authorizes submission.
- [ ] A successful submission receipt is retained without implying selection or approval.

No automation may check the maintainer-authorization item or submit the form implicitly.

## Proposed credit-use pilot — owner decision pending

This is a planning proposal, not a request already submitted or permission to spend.

**Recommendation:** prioritize the Codex Open Source Fund. The maintainer program remains a possible ecosystem-exception application; no adoption metrics or independent user outcomes have been established here.

**Proposed pilot:** 30 days after activation, capped at the lesser of $1,000 in awarded API credits or the actual awarded balance. No paid overage, no auto-recharge and no automatic extension. This is a conservative planning ceiling, not a measured cost forecast or claim of entitlement.

| Allocation | Ceiling | Deliverable |
| --- | ---: | --- |
| Open Core issue/PR review and regression assistance | $400 | Reviewed patches with verifier results tied to exact commits |
| Malformed-output and bounded reliability evaluations | $300 | Public protocol, fixtures, and retained positive/negative results |
| Documentation and reproducibility assistance | $200 | Kernel examples and reproduction instructions |
| Reproduction of failed trials and final reporting | $100 | Cost/evidence report and unresolved limitations |

Use only OpenAI API-billed models/tools permitted by the specific award. Reallocate only after owner approval; unused allocations remain unspent. Each run must identify the manifest revision, public input scope, model, task, token usage, reported API cost, evidence location and outcome. Stop at the ceiling or if scope/authorization is unclear. If available, use a dedicated API project with an enforced hard monthly spend limit below the authorized ceiling, plus a conservative run-level budget and usage reconciliation; hard-limit enforcement can lag slightly and alerts alone do not stop requests.

Days 1–7: establish public kernel tasks and baseline usage. Days 8–21: bounded maintenance/evaluation runs. Days 22–30: reproduce failures and publish a revision-bound report. Outcomes are proposed; no success rate or production reliability is promised. Research evaluations proceed only if permitted by the award; otherwise leave that allocation unspent.

Credits do not cover reserved implementation, third-party provider bills, salaries, hardware or unauthorized security work. Local non-model export validation is a separate check, not API consumption. Any evaluation tooling excluded by the manifest cannot be developed or improved under this Open Core request without an explicit scope/award decision; a pilot task may use only public inputs and included kernel or research material. This plan does not license or fund reserved tooling implicitly.

Awarded Fund API credits, any subscription-linked API credits, ChatGPT/Codex usage entitlements and promotional discounts have separate eligibility, expiration and billing rules. The $1,000 planning ceiling applies only if a Fund award is actually granted for these tasks. Before activation, confirm whether credits can be attributed to this project and how the platform consumes multiple grant balances; do not count subscription benefits or discount value toward the Fund pilot.

## Review evidence and decisions — 2026-11-22

Open Core Boundary [run #170](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/45015211388) passed at exact PR head `c13fc3b9a7fe85142fcfebece839bb2f290cf6ff` before this revision: 16/16 exporter fixtures, boundary validation (19 licensed entries, 33 reserved), static import closure (31 Python files), immutable 60-file archive (SHA-256 `a6293b9a51eab31bc9ecd700abbb823a7f14e9444cbefc31c02b538c0b548b0c`), and 10 isolated smoke imports. The earlier run #169 passed at `71ef7b7677b3b023842db75387b1d11f4ee00686`. Neither pass automatically qualifies a later documentation head; recheck the final head after edits.

At `c13fc3b9`, the same PR-triggered workflow set passed Measured evaluation acceptance binding, Clean install qualification, Control Plane and Factory ownership gate, but failed Maintainer approval gate, PR Agent advisory review, Command Station checks, Controller and provider contracts, and RESIDUAL Qualification v1. Some underlying jobs were cancelled/skipped. These failures are not erased by the scoped boundary PASS; root causes and current release readiness are not certified here.

Before submission, resolve:
- actual human collaborators and their roles;
- the effective existing license position and provenance representations, without changing scope implicitly;
- final candidate revision and a new boundary run if the application documents are revised after `c13fc3b9`;
- the proposed credit ceiling, public outputs and any research eligibility conditions;
- overlapping support or existing subscription benefit treatment, if relevant;
- whether to request Codex Security and what exact code it may access; do not assume path-limited scanning exists;
- final complete form contents, current terms and explicit owner submission approval.

Submission of Codex for Open Source itself accepts its program terms. An application must not assert that terms have no possible IP or confidentiality consequences merely because this draft reserves product code. The Fund similarity/non-exclusivity acknowledgment and any subsequent award terms also require personal review.

No private identifiers, submission, terms acceptance, benefit activation or licensing change are authorized by this document.
