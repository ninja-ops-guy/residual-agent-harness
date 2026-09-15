# FreeLLMAPI managed-service qualification

This qualification exists because a localhost proxy is still a **remote inference boundary** when it forwards prompts/evidence to upstream providers.

The dedicated `FreeLLMAPI qualification` workflow must pass before the managed onboarding change is merge-ready. It combines two forms of evidence:

1. **Deterministic failure-path regressions** prove readiness failure still scrubs `FREEAPI_CONFIG_JSON`, scrub failure tears the managed service down, the managed image is immutable-digest pinned, and generated configuration remains remote-classified.
2. **A live Docker smoke against the reviewed pinned image** starts real FreeLLMAPI, imports a non-production bootstrap marker through the same declarative config path used by onboarding, force-recreates the service without that config, and inspects the resulting container.

The live smoke fails unless all of the following are true:

- the running container reports the exact reviewed immutable image reference;
- port `3001/tcp` is published only on loopback;
- the bootstrap marker is absent from the long-lived container environment;
- `FREEAPI_CONFIG_JSON`, if present in the environment, is empty after scrub;
- the scrubbed service becomes reachable;
- a Residual harness built from the generated managed config rejects a private/non-cloud obligation as `local_only` **before** reserving any remote call or remote request bytes.

The workflow retains `runs/freellmapi-qualification.json` as a 30-day artifact containing the exact Git SHA, immutable image reference, Docker image ID, bind information, scrub result, and privacy-routing result.

This smoke intentionally does **not** make a paid upstream model call or claim provider quality, latency, quota, or cost. A user-supplied upstream key and FreeLLMAPI unified key are still required for the separate first-run worker-contract smoke performed by `residual setup`.
