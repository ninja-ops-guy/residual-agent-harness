# CI Expectations for Demo / Provider Changes

PR CI should prove deterministic source contracts and generated browser behavior. It cannot prove the final GitHub Pages origin before merge.

Post-merge Pages CI is therefore part of qualification, not a ceremonial deploy step. The deployment job must fail when published WebVM acceptance fails or when the published provider helper cannot load the real Puter SDK.

The real-SDK load check is intentionally non-authenticating and non-inferencing. A third-party outage can block a deployment qualification even when RESIDUAL code is unchanged; report that as `PROVIDER_SDK_LOAD` with the retained evidence rather than weakening or deleting the gate.

When availability of an external dependency makes release qualification impossible, keep the release BLOCKED/UNKNOWN until evidence exists. Do not replace the real-SDK gate with a fixture to obtain green.
