# PR #109 exporter repair and protected-review handoff

Current head: `fb99d5896b23b91e3903965a8c56813412533d48`.
Tree: `ed2d089f21273ec1e305d5ab432d554092267343`.
Accepted base: `9d88195a6329151197b53c05c6cbb5a74167f08f` (#124).

## Exporter repair delivered

`scripts/export_m4_artifact.py` now requires exactly six unique expected
names and rejects a declared uncompressed total above 16 MiB before emitting
archive bytes. The existing 1 MiB compressed limit and SHA-256 verification
remain. This bounds ZIP metadata totals; it is not an exporter claim to have
decompressed and validated every member.

Seven real-ZIP regression tests pass, including six missing-member subtests,
empty/extra/duplicate names, a highly compressed oversized payload and the
exact allowed size boundary. Reverting to the original subset check, dropping
duplicate detection, and removing the size bound each fails its targeted
assertions (`RuntimeError not raised`). `mutations.json` and the three logs
retain those results; the final source was restored and both test runners pass.
These are implementer-run regression proofs, not independent certification.

The validation source record binds the local prepared exporter tree to
published commit `fd08f8133ae05cd43a9f4a8bfbe55c7c1bac71b3` (tree
`e82a8b7b9ebe17a8cc10e10c22966c3a3b111996`). Refreshing main to `fb99d589`
only incorporates accepted demo files; `protected-blobs.json` also checks
that the tested exporter and regression blobs remain identical.

## Fresh qualification and CI

[M4 run 35017167706](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35017167706)
passes **142 cases + 84 subtests, zero skips** on synthetic merge `d43db468`,
whose tree exactly equals this head. The [complete retained archive](../../../qualification/m4/fb99d589/README.md)
matches GitHub's SHA-256 and contains all six expected members. The prior
run's stale base-event hint and actual merge identity are retained separately.

CI remains **RED**. Every inspected failed job in the refreshed PR workflows
names the lifecycle-test ownership mismatch. The completed full unittest jobs
report 1,017 cases, one ownership failure and 22 namespace skips. Matrix
siblings were cancelled; no complete Python matrix or full-pytest PASS is
claimed. `ci-checks.json` records the check results and job URLs;
`ci-failure-excerpts.log` retains the relevant diagnostics, not complete logs.

## Independent review and pin advancement still required

Only `tests/test_factory_runtime_lifecycle.py` differs from its protected pin:

- Accepted pin: `d4e00bd290351fa2ccd302ac578ac5dc463eda84`.
- Proposed blob: `85c6bf10a675ea3a74d775906d0bbaa79e411100`.

The other 37 protected files and the baseline itself remain unchanged.
`protected-test.patch` gives the exact before/after change. The earlier
[CLI repair and fault-injection evidence](../2551585f/README.md) remains
bound to its recorded source. All original alias, exit, JSON, stdout,
path-disclosure and empty-journal assertions must remain intact.

GitHub review 5215110153 is COMMENTED at the earlier `2551585f` head. It says
the proposed blob is technically acceptable but explicitly requires a genuinely
independent reviewer/maintainer before pin advancement. It is not approval;
the review snapshot is retained here. No acceptance of the current head is
inferred from that comment.

An independent reviewer must accept the protected test and review the CLI,
prerequisite and exporter changes on this candidate. Only then may the pin
for this file be deliberately advanced, with no qualification-claim expansion,
followed by fresh exact-head CI/qualification before merge. This continuation
implemented the repair and has not self-approved, changed the pin or merged
#109. Runtime/recovery, elapsed soak, blank-VM RC and ER1 remain downstream.
