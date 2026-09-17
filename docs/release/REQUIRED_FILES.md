# Release-Critical Demo / Provider Files

Treat changes to these as release-boundary changes requiring the guardrail review:

- `site/coi-serviceworker.js`
- `.github/workflows/pages.yml`
- `demo/vm/provider.html`
- `demo/vm/provider.js`
- `demo/vm/provider-session.js`
- `demo/vm/install_workbench.py`
- `demo/vm/browser_smoke.py`
- `demo/vm/provider_failure_smoke.py`
- `demo/vm/provider_sdk_smoke.py`
- `tests/test_webvm_publication.py`
- `tests/test_provider_release_guardrails.py`

The list is not exhaustive: path layout, service-worker registration, or provider navigation changes elsewhere can also alter the boundary.
