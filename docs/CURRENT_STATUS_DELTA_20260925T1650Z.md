# RESIDUAL current-status delta — 2026-09-25 16:50 UTC

This file is a documentation-only delta. Exact revisions do not inherit PASS, review, authorization, or release authority from earlier heads.

- Accepted `main` remains `d796f36b75e730a0bab71bdba564206174393719`; no newer pull request has merged since the preceding status snapshot.
- AUD-1 issue #353 remains OPEN with no milestone.
- Selected AUD-1 product candidate #448 remains `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`.
- F6 evidence-hardening successor #455 remains `a2567103c7e634310d696e421692fa1f86624e3b`. Qualification v1 run `36145155644` is PASS; Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, and Control Plane are PASS on that exact head. Final qualification artifact `10868469372` retains digest `sha256:f7311be30e192e786bf5f713562b01a58282d50870ea8699b97afec54b064017`.
- #455 maintainer approval remains FAIL (status target run `36145159290`), PR-Agent remains FAIL, and Vercel remains FAIL because of the account build/deployment-rate limit. These failures are not relabeled PASS and do not invalidate the separate exact-head technical workflow PASSes.
- Physical F6-A/F6-B remain BLOCKED / NOT EXECUTED. #455 explicitly does not inherit #453 execution authority; exact-head owner disposition and successor-bound physical F6 authorization remain required before execution.
- Master readiness ledger #427 remains `d9d49101ef0305c6460f028f4dccdd1a27299b71`. Qualification v1 run `36146616980`, Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, and Control Plane are PASS on that exact head; maintainer approval and PR-Agent are FAIL, and Vercel is FAIL from the account build/deployment-rate limit.
- Snyk PR #456 remains OPEN and unmerged at `77a556736aaa9ef0ba01fe3ee5b4f6194faa0e05`. It remains non-authoritative for accepted-main or v1 release claims.
- Documentation PR #454 remains OPEN / DRAFT and now has terminal exact-head CI on `1dd98b518425e2b88c2b9a98d5f98e39e714d8eb`: Qualification v1 run `36157746840`, Controller/provider `36157746872`, Command Station `36157746937`, clean install `36157746896`, Factory ownership `36157746873`, measured-evaluation binding `36157746929`, and Control Plane `36157746906` are PASS. Maintainer approval `36157746962` is FAIL, PR-Agent `36157746880` is FAIL, Vercel is PASS, and Snyk status is PASS. This qualifies only the documentation branch checks; it does not advance accepted-main, AUD-1, F6, canary, RC, soak, or release authority.

Release remains BLOCKED on current-head #455 human disposition and successor-bound F6 authorization, separately retained F6-A/F6-B evidence, post-F6 independent re-audit, Shared Comms disposition, PR-G26/27/28 closure, final claims/deployment-profile approval, accepted-main integration plus resulting-main qualification, exact-RC recovery/incident/provenance/elapsed-soak evidence, and explicit final release authorization.

This delta modifies documentation only. It does not modify Factory/M4 implementation, ownership baselines, qualification anchors, protected implementation bytes, or evidence schemas.
