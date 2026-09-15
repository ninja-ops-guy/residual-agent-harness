# Retained preparation validation

`summary.json` records three distinct executions: the initial broad sweep, the
focused preparation-tool tests, and the later selection after main reconciliation.
Their logs and JUnit XML remain separate. Do not combine them into a single
all-green run. The independent trust manifests live in `../trust/evidence/`.

The focused tools passed 85 tests and 48 subtests. The reconciled regression
selection passed 1,275 tests and 278 subtests, skipped 53 and failed one test at
host AF_UNIX socket creation. Its documented namespace-suite exclusions remain
qualification gaps. The original executable-bit failure was repaired by the
upstream traceability merge. The original text log's completeness is unconfirmed;
the original JUnit XML is complete and retained independently.

## Reconstruct the exact local source commits

Publication can preserve a tested Git tree while creating a different commit
identity. `source-history.bundle` retains the actual local preparation branches,
including the commits named by the test evidence and independent lanes. It ends
before its own addition, avoiding a self-referential archive. It contains code and
development artifacts only, and makes no new execution or authenticity claim.

The prerequisite commits are `dec571992a97b4ae80f0310aa32ffd8f542aef8c` and
`90dd2f40bff916e8b50d1777bf35debc511e996f`. In a clone that contains both:

```sh
(cd docs/program/validation && sha256sum -c source-history.bundle.sha256)
git bundle verify docs/program/validation/source-history.bundle
git fetch docs/program/validation/source-history.bundle 'refs/heads/*:refs/remotes/preparation-history/*'
git worktree add --detach /tmp/residual-preparation-reviewed 31dd64b77ca68fcd849c1760615776b4d2841381
```

A shallow clone must first obtain both named prerequisite commits from the
repository. Bundle verification does not execute
candidate code or call a model. Review the test selection and host prerequisites
before reproducing an execution.

The bundle checksum and per-artifact hashes provide consistency relative to an
external trusted source revision. Replacing both an artifact and its checksum
does not establish provenance; no standalone checksum here is a signature.
