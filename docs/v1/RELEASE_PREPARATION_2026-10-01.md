# v1 release preparation — 2026-10-01

Status: review-only repair and execution handoff. NOT an RC selection, approval,
merge, live-test authorization, or release. The existing Closure lane retains
single-writer control of product/helper convergence. No R4/R4.1 or sealed record
was changed or executed.

## Source identities inspected

| Role | Exact identity | Meaning |
|---|---|---|
| Accepted main | `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`, tree `7cd0d32be6fd61948f2fce753b122e5b6f0c6500` | Observed repository baseline, not a selected release |
| Release-control parent | #486 `9a247e313015a7daeee8aba089221b54debcf395`, tree `298662ceeed047aa865ac841f3e00684e79bf2be` | Direct current-main successor of the #478 release-receipt work; unmerged |
| Existing master read-model | #427 `9af9a6b2bab1ab36fa3f4b7f6d2536f448a645ff` | Planning/evidence index, not release authority |
| Frozen product candidate | #476 `05e01731208957e85cf72cf02a925b0660fca144`, tree `92276b7d9883a57fd061c749e319ec10b527d586` | Preserved unchanged; QD-2 line, not current-main qualification |
| Physical helper | #483 `558b37c2d552e20f18192c73a642b31038ee7b83` | Preserved unchanged and bound to #476; not this tooling repair |
| Owner-selected P1/v1 OpenClaw | #501 `c6669737e10d69657ba7ede2098e61bbfae64489`, tree `ed0d95e1378a3ceb453afa6114118351dfe6f693` | Software component tested; Station/lifecycle/native/live gates incomplete |

## Reproduced release-control defects

**RCP-01 — explicit expected RC identity was ignored before closure.** In the
parent `validate_binding`, expected source/tree/artifact comparison occurred only
inside the final `V1_CLOSED` branch. The earlier PRE_CLOSURE return, and either
ROLLED_BACK path, did not honor the supplied expectations. A real subprocess
invocation on a synthetic PRE_CLOSURE receipt with the wrong
`--expected-rc-source` returned exit 0 and `PASS: ... binding verified`.

**RCP-02 — ambiguous receipt JSON was accepted.** A synthetic receipt containing
`"state":"NO_GO","state":"GO"` in the same decision object returned the same
exit 0/PASS because the parser selected the last value. Duplicate top-level and
candidate keys, non-finite values, and overflowing JSON float syntax were also
not rejected at the input boundary. This is a draft validator finding, not proof
of an actual unauthorized production release.

Additional negative tests exposed untyped errors for malformed root/gate/closure
values, invalid encoding, excessive nesting, and large integer inputs. Those
errors did not demonstrate release acceptance; they are fail-closed reporting
and resource-boundary hardening.

## Repair

- Apply every supplied source/tree/artifact-set expectation in every phase,
  before any early return. A partial explicit expectation is never ignored.
- Continue requiring the complete externally selected identity/set for
  `V1_CLOSED`; retain all existing final-tag, gate-inventory and artifact checks.
- Reject duplicate keys at every JSON nesting depth, including identical values.
- Reject NaN, infinities and overflowing float syntax. Bound input to 4 MiB and
  integer syntax to 4096 digits; handle encoding/nesting/type failures explicitly.
- State that a successful CLI result verifies structural binding only, not
  release authorization. This tool still does not authenticate people, verify
  Git signatures, hash external artifacts, or replace JSON Schema validation.

No release gate, schema, signed/frozen identity, workflow, version, dependency,
product runtime, or existing assertion was weakened or replaced. Omitting
expectations before closure remains an internal-consistency check, not proof
that a candidate has been selected.

## Executed local evidence

The environment could not resolve github.com for a Git clone. The GitHub
connector supplied three exact parent files; their Git blob IDs were recomputed
locally and matched the API identities before any test:

- validator: `c38dcbd56235432b8c2f42c3cf6c162231b40513`
- existing tests: `b0868cc025a31b1e3c43c7cc83f45bd082708332`
- release gate JSON: `5a1420639ce99375b756c4d9ae9da71b717a3b0a`

Python 3.13.5 / Linux x86_64, temporary local files, synthetic receipts only:

| Campaign | Result |
|---|---|
| Original 18 tests against original source | 18 PASS |
| Initial 14 new tests against original source | FAIL: 29 failure entries including subtests, 3 errors |
| Final 16 new tests against original source | FAIL: 31 failure entries including subtests, 3 errors |
| Unchanged 18 existing + 16 new tests against repair | 34 PASS, zero failures/errors/skips |
| Wrong expected RC CLI differential | Parent exit 0/PASS; repair exit 1/explicit mismatch |
| Duplicate decision-key CLI differential | Parent exit 0/PASS; repair exit 1/duplicate-key rejection |

Published code/test blob IDs equal the locally tested bytes. Log digests and
actual differential outputs are in `release-preparation-local-results-20261001.json`.
Counts of subtest failures are not counts of separate product vulnerabilities.
Hosted whole-repository qualification and independent review remain required.
No local full-checkout, Windows, native OpenClaw, live-model, physical-F6,
blank-VM, recovery-drill, elapsed-soak, or deployment result is claimed.

## Dependency-ordered release handoff

This is a handoff to existing lanes, not a second master ledger or authority graph.

1. **Keep the agreed scope honest.** Docker and the owner-selected P1/v1 OpenClaw
   control plane are not silently deferred. The inspected #501 ledger reports
   Station integration, genuine native cancellation, external restart supervision,
   native OpenClaw testing and live-provider testing still incomplete. They are
   implementation/evidence gates, not paperwork. Optional OpenShell/R5 programs
   remain separate unless the owner explicitly changes scope.
2. **Reconcile the frozen product line deliberately.** #476's description forbids
   retargeting it; the master records current-main divergence and a pinned-versus-
   floating Open Core workflow conflict requiring owner disposition. Its existing
   PASS cannot qualify a new composition. Do not alter #476/#483 in this repair.
3. **Finish declared safety/profile/build inputs.** The inspected master still
   carries #426 receipt/recovery findings (repair or enforced exclusion), #487/#491
   security-policy alignment, PR-G26/G27/G28 source/provenance/locking and numeric
   operational objectives. These were not independently reproduced or cleared here.
   Resolve through their existing owners and evidence; do not declare them done
   from unrelated CI or drop them by omission.
4. **Review this narrow #486 repair and qualify exact bytes.** Passing this tool
   does not close the product, physical, signature, private-source or human gates.
5. **Select one converged product/helper pair under existing authority.** Qualify
   that exact pair, collect distinct physical F6-A/F6-B bundles, and obtain the
   independent post-F6 re-audit. A stale helper cannot validate a new product head.
6. **Freeze and qualify actual RC artifacts.** After approved convergence and
   authoritative-main qualification, settle version/build inputs, build once,
   retain provenance/SBOM/hashes, and qualify clean install, recovery, backup/restore,
   and the approved measured soak on those exact bytes. A short CI job named soak
   is not a 24h/72h wall-clock result.
7. **Authorize and release only from complete evidence.** Follow the existing
   release plan's bounded human gates, deployment/rollback window and final signed
   tag on the selected RC without rebuild. `EVIDENCE_INCOMPLETE` remains a stop.

There is no evidence-backed completion percentage or guaranteed date in this
handoff. The release clock starts from the actual selected complete scope and
its measured gates, not from individually green, unmerged feature branches.
