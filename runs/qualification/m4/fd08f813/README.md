# M4 archive after exporter hardening — superseded event head

[Run 35016795709](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35016795709),
job 104542138495, passed 142 cases and 84 subtests with zero skips. All 12
capabilities, including actual isolated execution, passed.

Event head: `fd08f8133ae05cd43a9f4a8bfbe55c7c1bac71b3`.
Event-head tree: `e82a8b7b9ebe17a8cc10e10c22966c3a3b111996`.
Actual checkout: `7d9438c01edfef6f2db9f19ed8b463bccbc9f373`.
Tested tree: `ed2d089f21273ec1e305d5ab432d554092267343`.

Main advanced while this run was being created. The actual synthetic merge
parents are accepted main `9d88195a6329151197b53c05c6cbb5a74167f08f` and
event head `fd08f813`; the event's `SOURCE_BASE` hint still says `1a52e9a2`.
The retained Git commit record, not that stale event hint, establishes the
actual source. The tested tree differs from the event-head tree by the five
accepted #124 demo files. This archive must not be described as a run of
tree `e82a8b7b`.

#109 was subsequently refreshed to `fb99d589`, incorporating that accepted
main and exactly matching tree `ed2d089f`. A separate fresh run on the
refreshed head is retained in [fb99d589](../fb99d589/README.md).

Artifact 10415892042 is retained byte-exact as `artifact.zip`, SHA-256
`8397ccd37709efce946ef42fed0e328c9189e50fd0da67b4cc50927fd550503f`.
Its 10,772 bytes match GitHub metadata. The six unique expected members were
read and retained; their declared uncompressed total is 51,809 bytes.
No source identity is silently amended and no independent acceptance or
release qualification is claimed by retaining this superseded attempt.
