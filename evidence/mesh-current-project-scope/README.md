# Current project scope for mesh provider replay

This draft successor to #551 enforces the existing project-membership rule
against the current persisted worker row, while retaining the caller-scope
restriction and all revocation, expiry, readiness, generation and lease checks.
The only production change is the three-line check in `MeshState.authorize`.

## Original failure and scope

Reviewed parent: #551 `489299d0884e22b26c1c02aae852d2e65eb09864`, tree
`5d9597f894568d02a0b603b6cbb2288c6e50bd76`. Its direct parent is #546
`2a3e4ff9feb7bcdba01ea2f385f63103d103f223`; the identical minimal
reproduction fails there. The archived `composition.json` records that ancestry.

After a disposable fixture narrows a stored worker's project scope, an earlier
authenticated handle is still authorized on the parent; a fresh handle is
denied. Four retained journal cases cover primary/fallback results in recorded
and accepted states. They return persisted evidence after scope removal, without
new provider calls or duplicate charges. Recorded results advance to ACCEPTED.

`original_scope_reproduction.py` and `original-findings.json` accompany
`original-evidence.zip`, which preserves both minimal failure logs and the four
raw observation files byte-for-byte, including their Windows line endings.
The original independent review had 16 fixture-setup failures
because `update_task` correctly prohibits direct lease/owner/attempt mutation.
Correcting only those disposable test setups yielded 24 passing affected cases;
the four scope failures remained. Historical counts are retained explicitly.

The demonstrated precondition is a trusted in-process caller holding an older
authenticated object after persisted scope narrowing. No public scope-edit API
or live remote exploitation is established. No native or multi-host qualification
is inferred from these fixtures.

## Regressions and qualification-fixture correction

`tests/continuity/test_mesh_scope_authority.py` covers both recorded and accepted
primary/fallback results, stale/current worker handles after scope removal,
unchanged-authority recovery without I/O or duplicate charges, and preservation
of a narrower supplied-handle scope. The original minimal reproduction is also
retained for independent exact-source replay.

The existing toxic-provider truncation test previously reached
`authority_rescinded` before provider execution. It now triages and claims its
disposable task, validates that lease and uses the prepared packet before making
the model call. Assertions require one actual loopback HTTP request, the existing
truncation denial and a task that remains running rather than accepted.
The archived `original-toxic-provider.log` retains the old 33-pass/1-failure run.

Reproduce the repository regressions:

```sh
python -m pytest tests/continuity/test_mesh_scope_authority.py tests/continuity/test_mesh_composition.py tests/qualification/test_toxic_provider_matrix.py -q
```

For the original minimal reproduction, set `MESH_REVIEW_EVIDENCE` to a new
disposable output directory and invoke pytest on `original_scope_reproduction.py`.
It must fail at the original source and pass with the correction. Exact published
revision results belong in the PR evidence; earlier candidate passes do not
transfer automatically.

## Ownership and remaining gates

The Factory ownership document, checker and 39-file manifest do not protect
`residual/station/mesh_state.py` or either test path. All 39 pins matched #551
before this change. No protected file, pin, checker, policy, credential or
permission change is part of this successor. Public mesh/scope branch and PR
searches found no competing current-row scope repair. #551/#546 remain unchanged.
The original checkout had no modifications to these scoped paths; its unrelated
worktrees, including a locked Hermes worktree, were preserved. Earlier app task
inventory did not return, so unpublished ownership visibility remains limited.

Independent review, exact-revision CI, full composition and installed/native
acceptance remain required. Human DCO/maintainer attestation and release gates
remain human responsibilities. This draft does not approve or merge any PR.
`V1_RELEASE_HOLD` remains active.
