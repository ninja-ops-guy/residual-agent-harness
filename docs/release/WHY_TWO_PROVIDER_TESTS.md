# Why There Are Two Provider Browser Tests

`provider_failure_smoke.py` deliberately intercepts the Puter SDK and supplies a deterministic test double. This is valuable because it can safely exercise sign-in gesture semantics, grants, bounded calls, failure redaction, Mission Control behavior, and fail-closed paths without external variability or spending provider allowance.

`provider_sdk_smoke.py` deliberately does the opposite: it must not intercept the SDK. It proves the real external script can initialize from the published Pages origin under the actual service-worker/header policy. It stops before sign-in or inference.

Removing either test creates a blind spot. They are complementary, not redundant.
