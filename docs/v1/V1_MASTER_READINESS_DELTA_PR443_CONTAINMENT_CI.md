# V1 readiness delta — PR-G26 containment repair terminal CI

Date: 2026-09-24. Status: **REPOSITORY TOOLING READY_FOR_REVIEW / PR-G26 BLOCKED / NOT VERIFIED**.

This append updates the pending hosted results in
`V1_MASTER_READINESS_DELTA_PR443_CONTAINMENT.md` without modifying that earlier
observation or its retained failing baseline. Ledger head observed before this
append: `07f7686643ccc9f2206fa146a78b01dc4568dd3b`.

## Exact identity

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`;
- #443 repair head: `4d70ddc7902237f4b7d1bd60ff1c82bd834e90a4`;
- repair tree: `59bb37151bdda4434531557f33d38cef8cca178a`;
- GitHub PR test-merge commit named in qualification artifacts:
  `28476c3e1f57fd57d46eded62686e72a328ef16d`.

The GitHub Git-commit endpoint was read for the test-merge commit. Its parents
are accepted main and the repair head above, and its tree is exactly
`59bb37151bdda4434531557f33d38cef8cca178a`, identical to the repair tree.
This is test-merge tree equivalence, not a merge into accepted main.

## Terminal hosted workflow results

All seven named technical workflows for the repair head completed successfully:

| Workflow | Run | Result |
| --- | --- | --- |
| Qualification-v1 | 36027756278 | PASS |
| Controller/provider contracts | 36027755996 | PASS |
| Command Station | 36027756038 | PASS |
| Clean install | 36027756115 | PASS |
| Factory ownership | 36027756068 | PASS |
| Control Plane | 36027755898 | PASS |
| Measured-evaluation binding | 36027755923 | PASS |

The controller/provider Python 3.13 job `107728512971` log reports 482 passing
contract/provider tests. That job runs `tests/contracts/` and `tests/providers/`;
it is not evidence that the 26 seal-manifest tests ran in that hosted job.
The **26/26 focused seal/containment tests, zero skips**, remain separately
identified local execution of the exact published source/test blobs.

GitHub reports final qualification artifact `10820442272`, named
`qualification-v1-final-28476c3e1f57fd57d46eded62686e72a328ef16d`, associated
with run `36027756278` and head `4d70ddc7...`, with archive digest
`sha256:ec723e40a78db2c5395fbaa922e3a0aad2289cf3b41ec617dd29398c92242317`.
This observation records artifact metadata; it does not claim a separate
redownload/hash recomputation or inspection of every artifact member.

## Separate unresolved review gates

PR-Agent run `36027755998` remains FAIL: secret preflight passed, advisory
review failed, and substantive-publication verification was skipped. This is
not substantive advisory evidence. No retry was issued by this remediation.
Maintainer run `36027756119` remains FAIL at explicit exact-head approval;
policy self-tests passed. No human review, approval or attestation is supplied
by these automated code/document edits.

## Disposition and limits

The reproduced symlink escape is repaired on #443 and repository-side tooling
is **READY_FOR_REVIEW / UNMERGED / UNACCEPTED**. Its remaining scope limitations
and original failing evidence are retained in the handoff and first delta.

PR-G26 stays **BLOCKED / NOT VERIFIED** pending independent review/freeze,
private authoritative-package/Seal v2 direct-source semantic and provenance
verification, explicit package-closure policy and independently retained evidence.
No corrected seal, canary, physical F6 execution, AUD-1 closure, deployment-profile
approval, RC, recovery/incident drill, elapsed soak, release/tag, production
acceptance or merge is authorized or established. No private/frozen artifact,
source research branch or live service was modified.
