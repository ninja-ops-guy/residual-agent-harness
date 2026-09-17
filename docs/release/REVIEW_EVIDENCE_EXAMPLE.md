# Example Scoped Evidence Report

Use this shape instead of a single ambiguous "demo PASS":

- Artifact identity: PASS — exact SHA `<sha>`.
- Generated WebVM desktop: PASS.
- Generated WebVM narrow Chromium: PASS.
- Published WebVM desktop: PASS.
- Published WebVM narrow Chromium: PASS.
- Provider deterministic fixture: PASS.
- Published real Puter SDK load: PASS.
- Provider real authentication: NOT_RUN.
- Provider real inference: NOT_RUN.
- Physical iOS/WebKit: NOT_RUN.

A release summary may be positive about the layers that passed, but must preserve NOT_RUN/UNKNOWN for stronger claims.
