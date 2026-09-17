# Demo / Provider Do-Not-Merge Conditions

Stop the merge when any applicable condition is true:

- candidate or deployed SHA is ambiguous;
- a service-worker/header change has not been evaluated for both `/demo/` and `/provider/`;
- `/demo/` is not cross-origin isolated;
- `/provider/` is cross-origin isolated;
- deterministic provider fixtures fail;
- generated desktop or narrow browser proof fails;
- a published-origin claim is based only on a generated/local artifact;
- the first post-merge Pages deployment fails;
- the published real Puter SDK load gate fails or was not run for a provider-affecting release;
- a physical iOS/WebKit claim is based only on narrow Chromium;
- a real inference claim is based only on test-double or SDK-load evidence;
- a prior first failure is being discarded in favor of an unchanged-code rerun.

Report the blocked layer explicitly and fix/requalify rather than weakening an adjacent boundary.
