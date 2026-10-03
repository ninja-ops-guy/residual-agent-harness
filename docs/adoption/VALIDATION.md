# Adoption preparation validation — 2026-10-03

Environment: Linux, Python 3.12.14; isolated test environment with pytest 9.1.1.
Implementation base: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`.
The PR's final HEAD/tree identify the proposed bytes. These are local source
checks; exact published-head CI and normal maintainer review remain required.

| Check | Observed outcome |
| --- | --- |
| Existing `examples/onboarding/demo.sh` at base | PASS; 2 accepted obligations, 0 model calls, result bound to trace |
| `python3 -m unittest tests.test_first_run -v` | 2 PASS; real CLI workflow including altered-result rejection from another working directory/path with spaces; pre-existing evidence preserved |
| `python -m pytest tests/test_onboarding.py tests/test_first_run.py -q` | 7 PASS, 2.09 seconds; includes the existing documented CLI blocks, missing-evidence failure propagation and tutorial validation |
| `python3 tools/first_run.py --output runs/adoption-reviewed-20261003` | PASS; zero model calls, expected totals, altered result rejected, original reverified |
| `python3 tools/check_open_core_import_closure.py` | PASS; 31 included Python files at unchanged base boundary |
| Exact-base Open Core export + isolated archive smoke | PASS; 60 files, 10 imports |
| Local Markdown links in all changed/new Markdown files | PASS; all local targets exist |
| Pilot CSV shape | PASS; header and all five unstarted rows contain 28 fields; missing measurements remain blank |
| `git diff --check` | PASS |

Exported base archive SHA-256:
`6847335bc6482a68002ef2bacec981b84dc06d96c5a0842d3ecc41236da30e60`.
This digest describes the source selection exported from the base, not a v1 RC.
No manifest or license scope was changed.

## Retained setup interruptions

- The first export invocation used a path outside the repository. The existing
  exporter correctly refused it with `output must stay inside the repository`.
  Repeating with a new `dist/` path succeeded; no exporter policy changed.
- The initial isolated pytest installation was blocked by this workspace's network
  sandbox. The authorized network-enabled retry succeeded. This was test setup,
  not a RESIDUAL product failure.

## Limits and next validation

This is not a full product suite, clean-machine install, Windows execution,
Docker/browser test, live-provider exercise, native OpenClaw qualification, recovery
exercise, elapsed soak or external-user pilot. The script uses portable Python
APIs, but local execution evidence covers Linux/Python 3.12.14 only. An archive
import smoke does not establish package-index installation or end-user usability.

The first-run JSON is explicitly advisory and carries `release_authority: false`.
It records Git identity/dirty state when available; it is not independent source
attestation. Existing qualification CI will discover `tests/test_first_run.py`;
no release workflow, protected pin or acceptance criterion is modified here.
