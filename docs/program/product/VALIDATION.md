# Product preparation validation record

This is local engineering evidence, not a confirmatory model experiment.
Machine-readable retained summary: [preflight-validation.json](preflight-validation.json).

| Check | Observed result |
| --- | --- |
| Reviewed/executed core source | `dec571992a97b4ae80f0310aa32ffd8f542aef8c` |
| Full Git tree | `6839c59babb5de81d0f9bb75de7f6c1e0b89e87b` |
| Preflight harness SHA-256 | `09de5c8363e2aeef223cdb13aa4a283193cbb9f1bddaacb2be6ffaecef374b59` |
| Bootstrap / fresh venv Python | CPython 3.12.14 |
| Host | Linux 6.18.44 / x86_64 |
| SQLite / Git | SQLite 3.53.1 / Git 2.51.1 |
| Fresh-venv source onboarding | PASS: 11 recorded phases |
| Provider/model calls | Zero; optional live smoke not requested |
| Evidence verification | Trace check and expected-root/result binding passed |
| Focused tests | 9 passed, 0 skipped |
| Blank Linux VM | NOT RUN: qemu, cloud-init, podman and docker unavailable; `/dev/kvm` absent |
| Installed wheel / live UI / namespace containment | NOT RUN by this lane |

Commands used:

```bash
python3 -m unittest discover -s tests -p test_clean_machine_preflight.py -v
python3 scripts/clean_machine_preflight.py --output /tmp/residual-product-preflight-final
```

The preflight source copy came from the committed core revision above. The harness
itself was under development outside that source archive; its exact file hash is
recorded separately. The compact JSON retains phase outcomes, timings, stdout/stderr
hashes, instruction hashes and artifact hashes. Full logs, result, trace and manifest
were retained at `/tmp/residual-product-preflight-final` in the execution workspace;
this temporary path is not a durable publication. The full manifest hash is
`74c9eb0c22b7f2f93f93b261c277dc4b74474cd8cbe998435b7a00faca50fbe6`.
Only the compact summary is committed. Reproduction produces new run IDs/timings;
compare validation outcomes and check newly produced hash bindings rather than
expecting all output bytes to match this run.

The focused tests exercise credential/Python-injection environment removal,
explicit paired provider opt-in flags, nonfinite/out-of-range timeout rejection,
archive traversal/link rejection, scripted result classification, command failure
retention, provider output withholding, failed source manifest generation, fresh
venv execution and trace/result binding, and refusal to overwrite evidence.

An initial development run failed because the first harness draft incorrectly
required at least one scripted-provider call. The quickstart sample was completed
entirely by deterministic solvers, with zero calls. The harness now accepts a
successful deterministic result with an empty call list and still rejects any
non-simulation provider call in the default path. The passing record above is from
the corrected harness; the original failed attempt is not counted as a pass.

The repository's existing `unshare` executable does not constitute a VM or prove
namespace privileges; parent integration checks reported namespace creation denied.
No blank-VM, interactive onboarding, Factory isolation, distributed-state, release
install-matrix, model performance, cost or production recovery claim is supported
by this local source fixture. Those remain the gates in the accompanying documents.
