# RESIDUAL current-status delta — 2026-09-25 13:48 UTC

This file is a documentation-only delta to the earlier `docs/CURRENT_STATUS.md` snapshot. Exact revisions do not inherit PASS or authorization from earlier heads.

- Accepted `main` remains `d796f36b75e730a0bab71bdba564206174393719`; no newer PR has merged.
- AUD-1 issue #353 remains open with no milestone.
- PR #455 is now at `72e934c96d9d34373cb6f4a012ee1a4c9df4ad5f` (tree `287e89442085a3d347ebf5a2ae0662b685031e9b`).
- #455 Qualification v1 run `36142877196` is PASS, including deterministic and aggregate jobs.
- #455 Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, and Control Plane are PASS on that exact head.
- #455 PR-Agent is FAIL at `36142880790`; maintainer approval is FAIL at `36142906854`; Vercel is PASS.
- Qualification final artifact `10867363132` reports digest `sha256:96b57aa786de6a891531376ab26dfc3ef1600c5b5cb8e1ecb4248ec601dd81bf`.
- Physical F6-A/F6-B remain BLOCKED / NOT EXECUTED because current-head human disposition and execution authorization are still absent. Earlier authorization on #453 does not transfer.
- PR #427 is at `d9985f16e887ec160f019ac17f3e2c27ef196ab3`; its named technical workflows are PASS while maintainer approval and PR-Agent are FAIL.
- Release remains BLOCKED on physical F6 evidence, independent post-F6 review, Shared Comms disposition, PR-G26/27/28 closure, final claims/profile approval, resulting-main qualification, exact-RC evidence, and explicit release authorization.

This delta modifies documentation only. It does not modify Factory/M4 implementation, ownership baselines, qualification anchors, protected implementation bytes, or evidence schemas.
