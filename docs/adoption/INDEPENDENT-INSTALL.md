# Bounded independent first-install gate

Status: gate mechanics implemented; **independent external evaluation is not yet evidenced**.
Until a qualifying external receipt exists for the exact candidate, the disposition is
`INDEPENDENT_INSTALL_UNVERIFIED`.

This gate answers one narrow adoption question: can an evaluator who was not given the
source checkout install one immutable RESIDUAL wheel handoff, complete the frozen offline
first run, inspect its evidence, and observe a deliberately altered result being rejected?
It does not qualify Station, OpenClaw, Docker, live providers, production recovery, security
hardening, release readiness, or broader platform support.

## Frozen supported configuration

The first gate supports exactly **Linux x86_64 + CPython 3.11**. The evaluator receives a
self-contained handoff directory containing the candidate wheel, all dependency wheels,
the standalone evaluator, the evaluation terms, `handoff.json`, and `handoff.sha256`.
Network access is forbidden during evaluation. No account, credential, model, Docker daemon,
Git checkout, repository clone, or local `examples/` directory is required or permitted as
an input to the result.

The handoff producer may use network access while assembling dependency wheels. That is a
packaging step, not part of the independent installation measurement. Every retained handoff
member is then frozen by size and SHA-256, and the manifest binds the repository, exact commit,
exact tree, candidate wheel filename, and candidate wheel SHA-256.

## Evaluation terms

1. Give the evaluator only the immutable handoff plus the expected `handoff.sha256` through a
   separately reviewable channel. Do not give them the source checkout or a prepared venv.
2. The evaluator must not be a repository maintainer, the development swarm, or the CI job that
   produced the artifact. A third-party person or independently administered host is acceptable.
3. Use a disposable host matching the frozen supported configuration. Do not add credentials,
   live providers, private repositories, or production data.
4. Do not coach the installation. If help is required, retain that fact and do not convert the
   attempt into an independent PASS.
5. Preserve the generated receipt and evidence directory without editing them. Redact only by
   producing a separately identified derivative; never rewrite the original evidence.
6. An `external` class plus `--attest-independent` is an evaluator assertion, not a cryptographic
   proof of organizational independence. Review the evaluator identity/process before promoting
   the receipt into a release or adoption decision.

## What the evaluator checks

The standalone `evaluate.py` first verifies the manifest checksum and every member hash. It then
requires Linux x86_64/Python 3.11, creates a fresh venv, installs the wheel and its dependencies
with `--no-index`, runs `pip check`, verifies that the imported `residual` package originates from
the installed distribution, and executes the deterministic inventory task with zero model calls.
It verifies the accepted trace/result pair, alters a copy of the result, requires rejection, and
verifies the untouched original again.

The negative control deliberately runs from a fake source tree containing a `residual` package
that raises `SOURCE_CHECKOUT_DEPENDENCY_TRIPWIRE` and poisoned `examples/onboarding` files with
wrong values. A successful run therefore demonstrates that the evaluated path used the installed
wheel plus evaluator-owned fixture rather than silently importing the checkout or reading the
repository's onboarding examples.

Retained evidence includes per-step logs, `pip freeze`, installed-package origin, accepted result,
trace, altered result, the negative-control disposition, candidate identity, handoff hash, host
fingerprint hash, evaluator classification, and a receipt hash.

## Producer command

Build the candidate wheel and dependency wheel(s), then freeze the handoff from the exact candidate
checkout. The PR workflow `.github/workflows/independent-install-gate.yml` performs this producer
step and publishes a repository-CI self-check artifact.

```bash
python tools/independent_install_gate.py prepare \
  --source-root . \
  --wheel dist/residual_agent_harness-0.5.0-py3-none-any.whl \
  --dependency-wheel dist/deps/defusedxml-*.whl \
  --terms docs/adoption/INDEPENDENT-INSTALL.md \
  --output runs/independent-install/handoff
```

Do not treat the repository-CI receipt as external evidence. Its required status is
`INDEPENDENT_INSTALL_UNVERIFIED` even when every technical check passes.

## External evaluator command

From the handoff directory or another directory that contains only the handoff, run:

```bash
python3.11 evaluate.py evaluate \
  --handoff . \
  --receipt external-receipt.json \
  --evidence-dir external-evidence \
  --evaluator-id '<approved pseudonymous evaluator id>' \
  --evaluator-class external \
  --attest-independent \
  --require-independent
```

Exit 0 with receipt status `INDEPENDENT_INSTALL_VERIFIED` is the positive gate result. Any technical
failure yields `INDEPENDENT_INSTALL_FAILED`. A technically successful run by repository CI,
maintainers, the development swarm, or an external evaluator who does not attest independence yields
`INDEPENDENT_INSTALL_UNVERIFIED`; that state must not be promoted to external proof.

## Candidate-bound receipt

The receipt is valid only for the exact `candidate.commit`, `candidate.tree`, `artifact.sha256`, and
`handoff_manifest_sha256` it records. Evidence from a predecessor or successor commit does not
transfer. The receipt also records `release_authority: false`: this adoption gate can support a
release decision but cannot select an RC, merge a PR, change licensing, or override existing v1
qualification and human-approval lanes.
