# PR Agent advisory boundary

PR Agent is an optional automated review assistant. Its output is advisory and does not
constitute independent review, maintainer approval, qualification evidence, security
assurance, or authorization to merge.

## Data boundary

When the workflow runs, pull-request metadata, descriptions, diffs, selected repository
context, and user commands may be sent to the configured model provider. Do not place
credentials, regulated data, production secrets, or other non-public sensitive material in
a pull request intended for automated review.

The repository secret `OPENAI_KEY` is supplied only to the pinned Action process. GitHub
does not pass repository Actions secrets to fork-triggered `pull_request` workflows.
This repository additionally skips automatic PR Agent execution for fork pull requests and
accepts comment-triggered commands only from OWNER, MEMBER, or COLLABORATOR associations.

## Authority and merge policy

PR Agent may identify possible defects and recommend changes. A maintainer must reproduce
or independently verify material findings against the exact PR head. PR Agent comments do
not satisfy the maintainer-attestation gate and must not be recorded as independent or
third-party evidence.

Automatic description replacement and automatic code improvement are disabled. Maintainers
may explicitly invoke supported slash commands after considering provider cost and data
exposure.

## Supply-chain boundary

The workflow pins `The-PR-Agent/pr-agent` to an immutable Git commit. Version 0.45.0's
Action builds from an upstream Dockerfile that references an upstream container image tag;
therefore the transitive container is not fully content-addressed by this repository.
Review the observed image digest in each Actions log before relying on a run. This residual
risk is a reason to keep the integration advisory and least-privileged.

## Failure behavior

A missing or empty `OPENAI_KEY` fails the workflow before PR Agent starts. Tool errors are
configured to propagate where supported. A green Action proves only that this automation
completed; it does not prove the reviewed change correct or merge-ready.
