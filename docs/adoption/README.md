# Try RESIDUAL and understand the result

RESIDUAL checks bounded work against declared requirements and retains the
evidence behind acceptance. Start by seeing a correct result accepted and a
changed result rejected. Then evaluate a useful task within the distribution
and permissions available to you.

## Choose the right surface

| Your goal | Starting point | Boundary |
| --- | --- | --- |
| Study or reuse the Open Core verification/research kernel | [Licensing](../../LICENSING.md), [manifest](../open-source/OPEN_SOURCE_MANIFEST.md), [funding readiness](../open-source/FUNDING_READINESS.md) | Only the manifest-scoped layer; a full-repository example does not qualify a standalone kernel package |
| Evaluate the development harness | Guided example below, in an authorized source checkout | Uses development runtime code outside the proposed Open Core; no license expansion |
| Evaluate Command Station and a real agent | [Station guide](../../START-HERE.md), after agreeing the evaluation artifact, terms, host and permissions | Reserved runtime; live inference and generated-code checks need explicit configuration |
| Assess v1 release readiness | [Existing master #427](https://github.com/ninja-ops-guy/residual-agent-harness/pull/427) and its latest delta | Open proposals and component tests do not authorize release |

The first public installation path must match the artifact actually distributed.
This guide does not claim that an installable Open Core package or v1 release
already exists. See the dated [baseline audit](BASELINE-2026-10-03.md).

## First run: no model or account

Prerequisites: a complete source checkout you are authorized to evaluate and
Python 3.11 or later. Git is useful for recording source identity. This example
requires neither Docker nor Bash. It starts no web service and downloads no model.
Run from the repository root:

```bash
python3 tools/first_run.py
```

On Windows:

```powershell
py -3 tools/first_run.py
```

The tool copies the synthetic inventory fixture into a new `runs/first-run`
directory, computes two totals, verifies their saved evidence trace, alters a
separate copy of the result, requires that copy to be rejected, then checks the
original again. It preserves the checkout's sample and previous runs.

Expected outcome:

- Accepted inventory totals: **7,230 RPM** and **65.25 degrees C** (sum of readings).
- The altered result is rejected; the original remains valid.
- `runs/first-run/first-run.json` reports `status: PASS`, `model_calls: 0` and
  `release_authority: false`.
- `accepted/result.json`, `accepted/trace.jsonl` and per-step logs remain available.

The fixture is deterministic; no live agent performs this task. PASS means this
example completed and this alteration was rejected. Hashes and trace binding do
not prove independent authorship, general correctness or an attacker's inability
to replace both files. This is not an authoritative qualification receipt.

To repeat, preserve the earlier evidence and choose a new output directory:

```bash
python3 tools/first_run.py --output runs/first-run-2
```

For the underlying CLI commands, continue to the [source quickstart](../quickstart.md).

## If it stops

| Message or observation | Next step |
| --- | --- |
| Python command not found | Install the Python version admitted for your evaluation host; on Windows check `py -3 --version` |
| Output path already exists | Choose a new `--output` directory; no previous run is replaced |
| `tools/first_run.py` missing | Use the exact checkout containing this guide/tool; record its commit |
| Sample run or verification failed | Inspect `first-run.json` and the named `.log`; record the first failure before retrying |
| Missing module/import | Check Python version and that this is a complete development checkout, not a manifest-only export; do not copy reserved files into an Open Core artifact |
| Altered result was accepted | Stop; preserve both artifacts and report the verifier failure through [SECURITY.md](../../SECURITY.md) if security-sensitive |

Before sharing any diagnostics from your own work, remove credentials, private
source and personal information. The bundled fixture itself contains synthetic
inventory values.

## Next: one useful bounded task

For authorized runtime pilots, the proposed initial use case is a small coding
change with explicit allowed files, a fixed budget, known acceptance checks and
human review. Select one existing supported agent integration for that pilot.
OpenClaw remains an owner-required v1 feature, subject to its own native/live and
final-composition gates; its presence in a proposal is not qualification.

Use a disposable repository with a known test and a small change such as repairing
one function. Before starting, write down the baseline commit, expected behavior,
allowed files, maximum calls/tokens and stop condition. Inspect the diff and test
results before accepting anything. Record manual intervention and unknown usage.
Compare with doing the same class of task using your existing agent workflow.

Follow [START-HERE.md](../../START-HERE.md) for the current Station interface. The
shipped release must replace development instructions with its exact installation,
support and recovery contract. The [pilot protocol](PILOT.md) defines how to test
that journey with external users without treating training output as adoption.

## Maintainer work order

This is an adoption workstream attached to the existing v1 master, not another
release authority or a replacement for technical gates. Owners below are proposed
roles, not claims that anyone has accepted an assignment.

| ID | Deliverable and acceptance | Proposed owner | Initial state / existing lane |
| --- | --- | --- | --- |
| AD-01 | One audience, one useful bounded coding workflow, explicit edition and terms | Product/maintainer | Proposed workflow above; final distribution/terms remain in #427 |
| AD-02 | One new-user path runs from the actual delivered artifact with no hidden source checkout dependency | Packaging + onboarding | Source walkthrough prepared here; released-artifact install remains unproven; #427 / #474 |
| AD-03 | Public claims, OS/provider support and licensing agree with the selected release | Claims + release owner | Entry-point corrections here; full reconciliation belongs to #477 / #482 / #427 |
| AD-04 | One end-to-end agent integration completes useful work, cancellation/restart and evidence inspection | Integration owner | OpenClaw is required in v1; existing #511 and successor/native qualification lane; no duplicate implementation here |
| AD-05 | Failure, budget exhaustion, safe stop/retry, backup and upgrade are understandable on the exact artifact | Runtime + release owner | Existing recovery/operations gates in #427; conduct user exercise only after prerequisites |
| AD-06 | Five external participants try the same frozen onboarding, with every attempt recorded | Pilot coordinator | NOT_STARTED; [protocol](PILOT.md) and [scorecard](pilot-results.csv) prepared |
| AD-07 | At least three useful completions and two voluntary returns within 14 days | Pilot coordinator | Proposed learning targets; no adoption evidence yet |
| AD-08 | Reproducible evidence of a benefit after setup, runtime and intervention costs | Evaluation owner | NOT_STARTED; small pilot is descriptive, not a general research result |

Execute AD-01/02/03 preparation now; coordinate AD-04/05 with their existing owners.
Run external artifact installation only once the artifact and terms are explicit.
Publish broader claims only after applicable release gates and human authority.

The initial pilot target is 4/5 unaided installations within 15 minutes, 3/5 useful
task completions and 2/5 voluntary returns within 14 days. These are proposed
learning thresholds, not existing release policy, statistical proof or substitutes
for security qualification. A failed pilot should result in a specific repair and
a new cohort/version, with the original outcomes preserved.

The supplied authority-preserving recovery report is addressed in the
[research intake](RESEARCH-INTAKE.md). Its applicable lessons strengthen pilot
failure-state checks; the separate research program does not silently expand v1.
