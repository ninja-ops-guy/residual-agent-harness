# Production Gate Invariants

1. Public artifact identity is exact-SHA bound.
2. `/demo/` isolation and `/provider/` non-isolation are simultaneously required.
3. Deterministic provider fixtures remain mandatory but are not external-network evidence.
4. The first published deployment of a merged provider/demo change must load the real Puter SDK from the real public origin.
5. SDK-load CI stops before authentication/inference.
6. Authentication and real inference are separately reported when exercised.
7. Narrow Chromium and physical WebKit are separately reported.
8. First failures are retained and never erased by unchanged-code reruns.
9. Unknown evidence remains UNKNOWN/BLOCKED; agents may not upgrade it by inference.
