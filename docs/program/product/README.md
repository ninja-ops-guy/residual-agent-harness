# Product preparation program

Status: **design freeze candidate; release and production qualification are pending**.
Reviewed implementation: `dec571992a97b4ae80f0310aa32ffd8f542aef8c` (Git tree
`6839c59babb5de81d0f9bb75de7f6c1e0b89e87b`). These documents describe that
exact baseline, not an assertion about later merges or PR #81.

| Lane | Deliverable | Completion boundary |
| --- | --- | --- |
| 11 / DSM-004 | [Ownership and distributed-state protocol](DSM-004.md) | Reviewable protocol and acceptance tests; no new consensus backend |
| 12 / PROD-007 | [Recovery design and operator runbook](PROD-007.md) | Restart matrix and executable-test requirements; no HA/SLO claim |
| 19 | [v1.0.0-rc1 release gates](RELEASE-RC1.md) | Exact supported profiles and evidence required before tagging |
| 20 | [Clean-machine onboarding protocol](ONBOARDING.md) | Runnable fresh-venv source check; actual blank VM remains pending |
| 21 | [Trust-boundary threat model](THREAT-MODEL.md) | Mechanisms, assumptions, known gaps and required evidence |

The preparation code is deliberately outside `residual/factory/`. Run it with:

```bash
python3 scripts/clean_machine_preflight.py --output /tmp/residual-onboarding-evidence
python3 -m unittest discover -s tests -p test_clean_machine_preflight.py -v
```

The output directory must be new. The default run makes no model calls and
uses an archive of committed source, so a modified working file cannot silently
change the tested core. The first command tests the checkout's current `HEAD`;
the retained manifest identifies its actual SHA/tree and instruction hashes.
`source_archive_sha256` binds only the archived onboarding subset; `git_tree`
identifies the full Git tree. Neither is an external authenticity anchor.

See [local validation](VALIDATION.md) for the actual executed scope. None of
these preparation results belongs in the confirmatory R0–R5 dataset.
