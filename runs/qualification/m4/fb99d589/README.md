# M4 candidate evidence — refreshed head and complete archive

PR #109 head `fb99d5896b23b91e3903965a8c56813412533d48` includes accepted
main `9d88195a6329151197b53c05c6cbb5a74167f08f` (#124).
Synthetic merge: `d43db468ee1075bb0f2612ef75575afa0ac01d5f`.
Both candidate and tested trees: `ed2d089f21273ec1e305d5ab432d554092267343`.
The retained Git commit record confirms the actual parents and tree; the
source-environment report agrees and tracked source was clean.

[Run 35017167706](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35017167706),
job 104543392283, passed real isolated execution and all 12 capability probes.
Environment: Ubuntu 22.04 image `20260907.292.1`, kernel `6.8.0-1064-azure`,
Python 3.12.14. **142 cases plus 84 subtests passed, zero skips**, in 20.85s.
JUnit has 142 testcase elements; the aggregate also counts the 84 subtests.
No failure, error or skipped elements occur. The seven additional cases and
six additional subtests exercise the archive-export guards.

Artifact **10416235755**, retained as `artifact.zip`, has SHA-256
`49fa75e9c39e13a102bb16b20346e2875f42eac0b83f539ed137f78bc527db6a`.
The recovered ZIP is 10,725 bytes, matching GitHub's independent artifact
metadata digest and size. It contains exactly six unique expected files,
51,809 declared uncompressed bytes; every member was read and compared with
its retained copy. The report, source identities, test log and JUnit agree.
Installed dependencies are retained observations, not a frozen ER1 lockfile.

`workflow.log` retains the bounded byte export used to recover the archive.
`verification.json` records the checks; `SHA256SUMS` covers the retained files.
The preceding [fd08f813 run](../fd08f813/README.md) records why the branch
was refreshed after accepted main advanced during CI.

This qualifies the named M4 candidate tree. The protected lifecycle test
still awaits independent acceptance and deliberate pin advancement; ordinary
CI remains red. See the [review handoff](../../../reviews/pr109/fb99d589/README.md).
It does not establish merged-main or future-RC qualification, elapsed soak,
blank-VM installation, canonical demo acceptance or research results.
