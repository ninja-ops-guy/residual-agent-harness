# Release Agent Entry Point

For demo/Pages/provider/browser work, read in this order before editing or recommending merge:

1. repository `AGENTS.md`
2. `docs/release/DEMO_REGRESSION_GUARDRAILS.md`
3. `docs/release/DEMO_RELEASE_CHECKLIST.md`
4. relevant current release/stabilization document
5. retained regression postmortems relevant to the touched boundary

Do not claim a layer PASS from adjacent evidence. In particular: fixture provider != real SDK load != authentication != real inference; narrow Chromium != physical iOS/WebKit; generated artifact != published origin.
