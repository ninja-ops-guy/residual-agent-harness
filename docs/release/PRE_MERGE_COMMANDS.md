# Pre-Merge Commands

At minimum, applicable CI must execute the equivalent of:

```bash
node --experimental-default-type=module --test tests/webvm-provider.test.mjs
python -m unittest -v tests.test_webvm_publication tests.test_provider_release_guardrails
```

The Pages workflow additionally builds the actual WebVM artifact and runs desktop+narrow Chromium browser proof. Do not substitute these quick commands for the full Pages/browser qualification when the change affects release behavior.

The real Puter SDK load test intentionally belongs to the post-deploy published-origin job; running it against a local static server cannot reproduce the complete Pages/root-service-worker environment that caused the incident.
