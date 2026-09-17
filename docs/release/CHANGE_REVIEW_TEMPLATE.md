# Demo / Provider Change Review Template

Use in PR descriptions or reviews for changes touching browser/demo/provider release surfaces.

**Exact head:** `<sha>`

**Touched acceptance layers:** artifact identity / generated WebVM / published WebVM / provider fixture / real SDK load / provider auth / provider inference / physical device

**Service-worker/header map:** Describe which worker controls `/demo/` and `/provider/`, and the expected COOP/COEP/CORP behavior for each.

**Evidence run:** Record exact-head deterministic tests and generated browser proof. After merge, record the first production Pages run and published-origin evidence.

**Provider claim:** State separately whether fixture coverage, real SDK load, auth, and real inference are PASS / FAIL / NOT_RUN / UNKNOWN / BLOCKED.

**Device claim:** State the actual browser engine/device class. Never promote narrow Chromium to physical iOS/WebKit evidence.

**First-failure retention:** Link retained first failure if one exists; do not replace it with an unchanged-code rerun.

**Merge decision:** If any required layer is NOT_RUN/UNKNOWN/BLOCKED, do not claim the broader release surface qualified.
