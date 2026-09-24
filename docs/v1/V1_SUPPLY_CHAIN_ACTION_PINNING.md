# RESIDUAL v1 GitHub Actions dependency-pinning qualification

Status: **release preparation / validation only**. This document does not authorize a merge, deployment, canary, tag, release, or production mutation.

## Scope

Production-readiness audit PR #423 identified supply-chain pinning as `PR-G27`: GitHub Actions and other build dependencies must have explicit provenance and tamper-resistant identity before production closure.

A read-only code search against exact accepted `main@d796f36b75e730a0bab71bdba564206174393719` found mutable major-tag references in release-relevant workflows, including `actions/checkout@v4` and `actions/upload-artifact@v4`. The presence of a floating tag is the observed gap; this lane does not infer compromise or a past supply-chain incident.

## Proposed acceptance rule

For every `.github/workflows/*.yml` and `.yaml` file:

1. external GitHub Actions and external reusable workflows MUST use an immutable 40-hex commit SHA after `@`;
2. repository-local actions/workflows beginning with `./` are outside this gate because they are already bound to the repository commit under qualification;
3. `docker://` step references are reported outside this specific action-ref gate and require their own image-digest policy before production use;
4. human-readable version comments such as `# v4.2.2` MAY accompany a commit SHA but MUST NOT replace it;
5. dynamic, branch, major-tag, semver-tag, or unqualified external refs are `BLOCKED`;
6. the validator is read-only and MUST NOT resolve tags over the network, rewrite workflows, or claim that a pinned commit is trustworthy merely because it is immutable.

Passing this rule proves only immutable workflow dependency identity. PR-G27 still requires review of the selected commits, dependency provenance/SBOM/signature policy where applicable, and exact-head CI after any pinning remediation.

## Tooling in this lane

`scripts/validate_github_action_pins.py` scans workflow `uses:` directives and emits `residual.github-action-pin-audit.v1` with `PASS | BLOCKED`, counts, and exact path/line/target violations. It exits non-zero on a blocked result and labels its output `VALIDATION_ONLY`.

`tests/test_github_action_pins.py` covers immutable commit pins, mutable semver/branch refs, external reusable workflows, repository-local actions, Docker references, quoted targets, comments, and fail-closed behavior when the workflow directory is absent.

## Remediation boundary

This PR intentionally does **not** bulk-rewrite active workflows. Pinning should be a separately reviewed remediation after each currently selected action/tag is resolved to an exact commit and the repository confirms that existing workflow-policy tests (including checkout credential-persistence checks) are reconciled without weakening their security assertion.

After remediation, qualification should run the validator against the exact candidate tree and retain its JSON output as release evidence.
