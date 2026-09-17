# Executable Regression Gates

The durable protections are executable, not documentation-only:

- `tests/test_webvm_publication.py` pins the `/provider/` COI bypass ordering.
- `tests/test_provider_release_guardrails.py` pins the production gate and forbids auth/inference/route interception in the real-SDK smoke.
- `demo/vm/provider_failure_smoke.py` retains deterministic provider protocol/error-path browser coverage.
- `demo/vm/provider_sdk_smoke.py` loads the real external SDK from the published origin.
- `.github/workflows/pages.yml` requires the published real-SDK check after deployment.

The surrounding release documents tell agents how to interpret and preserve these gates.
