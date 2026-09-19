# Browser production-readiness runner

Fast browser/operator qualification for RESIDUAL release candidates.

## Run

```bash
npm install
npx playwright install chromium
npm run test:readiness
```

Quick loop:

```bash
npm run test:readiness:quick
```

Test a deployed candidate instead of starting a local Station:

```bash
RESIDUAL_QA_URL=https://example.invalid npm run test:readiness
```

Bind evidence to the tested revision:

```bash
RESIDUAL_QA_REVISION="$(git rev-parse HEAD)" npm run test:readiness
```

Set `HEADED=1` for interactive debugging and `RESIDUAL_QA_VIDEO=1` to retain video.

## What it gates

The runner rapidly checks:

- Station startup and bootstrap/API contracts.
- Browser landing/render health.
- Training mission through integrated state.
- Receipt/evidence discoverability and verified-release export.
- Operator-note HTML escaping.
- Provider credential redaction after reload.
- Diagnostics, chain verification and JSONL export.
- 390px browser layout overflow.
- Reload/state continuity.
- Visible repair/retry/restart/recover/resume/triage/fix controls for obvious disabled/no-op states.
- Browser page errors, console errors and request failures.

Every failure captures a full-page screenshot and HTML snapshot. A Playwright trace, network/console/page-error/request-failure JSONL logs, server stdout/stderr, `report.json`, and `summary.md` are retained under `runs/browser-readiness/<timestamp>/`.

## Rapid iteration contract

Use `quick` while iterating. Use `full` on the frozen RC. A failed gate exits non-zero and preserves all diagnostics; do not rerun a failed release candidate merely to replace the first failure with green evidence.

The report includes `revision`. For release evidence, always set `RESIDUAL_QA_REVISION` to the exact tested SHA.

## Non-claims

This runner is deliberately browser-scoped. PASS does **not** replace:

- capable-runner M4 qualification;
- true blank-VM install/reinstall/upgrade evidence;
- host-loss/recovery qualification;
- elapsed 24h/72h soak;
- physical iPhone/Safari acceptance;
- a real-account Puter provider → candidate → verifier → receipt success.

Those remain separate production-readiness gates.
