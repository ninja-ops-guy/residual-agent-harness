# Agent Summary — Demo Regression Prevention

If you touch demo/provider/Pages/browser policy, remember three separations:

**Path boundary:** `/demo/` needs WebVM isolation; `/provider/` must not inherit it.

**Evidence boundary:** fixture provider tests prove deterministic RESIDUAL behavior; published real-SDK loading proves browser/network policy; real authentication/inference require separate retained evidence.

**Device boundary:** narrow Chromium proves narrow Chromium, not physical iOS/WebKit.

Never merge by extrapolating across these boundaries. Use the release checklist and acceptance-layer matrix, retain first failures, and report untested layers as NOT_RUN/UNKNOWN.
