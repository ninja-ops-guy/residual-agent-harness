# Provider Gate Scope

The automated production provider gate intentionally stops at SDK initialization. It proves the published provider helper can fetch and initialize the real Puter browser SDK under the actual GitHub Pages service-worker/header environment.

It does not authenticate, enumerate models, consume credits, or run inference. Those are separate acceptance layers. This separation prevents CI from creating accounts or spending provider allowance while still catching origin-policy regressions that deterministic test doubles cannot detect.

The deterministic provider fixture remains required for RESIDUAL protocol, authorization, error redaction, and fail-closed behavior. Neither gate substitutes for the other.
