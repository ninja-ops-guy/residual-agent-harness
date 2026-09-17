# Demo Release Checklist

Use this checklist for every change that can affect Pages, WebVM, Mission Control, provider setup, service workers, navigation, caching, or browser policy.

- [ ] Record exact candidate SHA.
- [ ] Confirm `/demo/` remains cross-origin isolated.
- [ ] Confirm `/provider/` remains non-isolated.
- [ ] Run deterministic provider protocol/error-path fixtures.
- [ ] Run generated desktop Chromium WebVM proof.
- [ ] Run generated narrow Chromium proof; label it narrow Chromium, not physical mobile.
- [ ] Merge only after applicable exact-head gates pass.
- [ ] Treat the first production deployment of the merged SHA as authoritative.
- [ ] Verify published `/demo/build-info.json` is the merged SHA.
- [ ] Verify published guest boot/shell, `demo`, `verify-demo`, warm reload, Mission Control and workbench.
- [ ] From published `/provider/`, click `Load Puter` and prove the REAL `js.puter.com/v2/` SDK initializes with no CORP/COEP/CSP/network failure.
- [ ] The SDK-load gate MUST NOT sign in, list models, or invoke inference.
- [ ] If real provider inference is claimed, retain separate real-account candidate -> verifier -> receipt/artifact evidence.
- [ ] If physical iPhone/WebKit is claimed, run that physical/runtime class separately.
- [ ] Retain failures and classify them by layer. Do not rerun unchanged code merely to replace red evidence with green.

See `DEMO_REGRESSION_GUARDRAILS.md` for rationale and agent rules.
