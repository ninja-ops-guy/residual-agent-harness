# Provider Failure Triage

When provider setup fails, identify the earliest failing layer:

- Provider tab does not open: Mission Control/navigation/channel setup.
- Provider tab opens but is `crossOriginIsolated`: root service-worker/header scope regression.
- `Load Puter` fails and `js.puter.com` request fails: `PROVIDER_SDK_LOAD`; inspect CORP/COEP/CSP/network/content blockers.
- SDK loads but sign-in fails: `PROVIDER_AUTH`; inspect popup/user activation/session behavior.
- Sign-in succeeds but request never dispatches: provider grant/authorization/channel state.
- Request dispatches but provider rejects: `PROVIDER_INFERENCE` transport/model/account layer.
- Response arrives but envelope is rejected: `PROVIDER_PROTOCOL`; inspect bounded protocol detail, never raw secret output.
- Candidate reaches guest but fails verification: RESIDUAL candidate/verifier layer, not provider connectivity.

Keep evidence from each layer separate so a fix does not accidentally weaken another boundary.
