# Demo Acceptance Evidence Naming

Use explicit names in CI artifacts and reports so evidence cannot be mistaken for a stronger layer:

- `generated-webvm-desktop`
- `generated-webvm-narrow-chromium`
- `published-webvm-desktop`
- `published-webvm-narrow-chromium`
- `provider-fixture-protocol`
- `published-provider-real-sdk-load`
- `provider-real-auth`
- `provider-real-inference`
- `physical-ios-webkit`

Do not name narrow Chromium artifacts `mobile` without the engine qualifier in human-facing release summaries. Do not call provider fixture or SDK-load evidence `real provider inference`.
