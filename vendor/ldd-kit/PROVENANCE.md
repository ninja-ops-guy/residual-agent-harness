# LDD integration provenance

Upstream: https://github.com/ninja-ops-guy/LDD-Kit

Pinned commit: `ac8bee365205db333d92d9fd8f996d68d18c2e5b`.

The original `base.json`, `config.yaml`, `SPEC.md`, and README license text are included in this directory. `residual/station/schemas/ldd-base.json` is a byte-identical copy of the upstream base schema and its required event fields are checked by the runtime adapter before the stricter workflow contract.

The integration implements a Python workflow adapter with strict payload checks, a transactional reducer, task ownership/leases, and deterministic Markdown/report generation. Existing upstream log-pattern validators were not repurposed as runtime validators: they do not enforce task identities or allowed state changes.

The upstream Jinja generator and incompatible CI templates are not on this application's setup path. This application has direct, tested Python/JSON configuration and its own CI workflow. It retains the existing RESIDUAL model transports and accounting contract.

No upstream repository was modified. This bundle is an integration in the RESIDUAL repository, not a claim that the entire upstream observability toolkit has been repaired or embedded.
