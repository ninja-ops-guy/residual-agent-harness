# Independent review policy

## Rule

Every pull request merged to `main` requires at least one independent human `APPROVED` review bound to the exact current PR head, in addition to all required CI and qualification gates.

An approval qualifies only when all of the following are true:

- the reviewer is not the pull-request author;
- the reviewer is a human GitHub user rather than a bot/application identity;
- the review state is `APPROVED` on the exact current head SHA;
- no later meaningful review from that reviewer on the same head requests changes or is dismissed;
- GitHub reports the reviewer has repository `write` or `admin` permission at gate evaluation time.

The write-authority requirement intentionally mirrors GitHub's required-review merge semantics. On a public repository, an arbitrary outside account may be able to submit an approval; that approval is useful feedback but is not merge authority for this policy.

`COMMENTED` reviews, author/self review, bot review, approval of a stale head, approval from a read-only/untrusted outside account, missing reviewer-authority data, UNKNOWN/BLOCKED evidence, or green CI alone do not satisfy independent acceptance.

## Why this is repository-wide

Security, runtime, release, evidence, onboarding, observability and qualification changes already rely on independent acceptance language. A path-scoped rule would leave merge authority dependent on classification heuristics. Requiring one authorized independent current-head approval for every `main` PR is simpler, auditable and fail-closed. Low-risk documentation changes still receive the same lightweight second-person check.

## Protected M4 and qualification changes

This policy does not replace stricter gates. Changes to protected M4 controls/tests/schemas still require their existing sequence, including capable-runner real execution, zero skips, no promotion of UNKNOWN/BLOCKED to PASS, independent review before ownership-pin advancement, and fresh qualification after an accepted protected change.

## Machine gate

`.github/workflows/independent-review.yml` runs `scripts/check_independent_review.py`. The check passes only when GitHub exposes a qualifying independent approval for the exact current head **and** the reviewer-permission endpoint confirms write/admin repository authority.

Reviewer permission lookup is fail-closed. A missing collaborator record, read-only permission, unrecognized permission value, API failure or unavailable permission evidence cannot become PASS.

The workflow is not merge enforcement by itself. Repository ruleset `23436488` must also require the `independent-review` status check and should set `required_approving_review_count` to at least `1`. Keep stale-review dismissal and strict required-status behavior enabled. GitHub's native required-review rule remains an independent platform backstop; the custom check is not a substitute for it.

## Historical review debt

A merge that predates enforcement is not retroactively rewritten as having had a pre-merge approval. Any required post-merge independent audit should be retained explicitly as post-merge evidence. In particular, merged PR #136 retains its historical pre-merge review gap.

## Failure behavior

If review identity, PR head identity, GitHub review data, reviewer repository authority, or API access cannot be established, the gate returns BLOCKED/nonzero. It never converts missing review or permission evidence into PASS.
