# Frozen adversarial verifier challenge set v1

This is a **non-confirmatory engineering corpus**: 16 inert candidates, eight
defects and eight correct controls, across eight challenge categories. No model
or production verifier has been evaluated by adding it. It is separate from the
R0–R5 workload and must not be incorporated into a confirmatory dataset after
results have been inspected.

The byte-level manifest SHA-256 is:

`ee94c35c2fa823386b195c778b5540c98ca710fe4a4ac33e4b5f38c17aa36756`

`manifest.json` locks every candidate, the evaluator labels, and the fault
matrix by SHA-256. The validator pins the manifest hash separately, so changing
a candidate and merely regenerating the manifest fails validation. This is a
version-controlled content freeze, not a signature or defense against an
operator who can replace the validator and its expected hash. Preserve the
reviewed commit externally when using this set in a retained experiment.

## Commands

Run these from the repository root; they need only the Python standard library:

```sh
python scripts/validate_adversarial_corpus.py validate
python scripts/validate_adversarial_corpus.py export > /tmp/verifier-inputs.jsonl
python scripts/validate_adversarial_corpus.py score --outcomes /tmp/verifier-observations.json
python -m pytest -q tests/test_adversarial_corpus.py
```

The export emits only candidate envelopes: `schema`, neutral `case_id`, `task`,
and `artifact`. It does not emit category names, labels, rationales, or witness
inputs. Mount or pass **only this export** to a verifier. Never expose the corpus
directory, this README, gold labels, or tests to the verifier under evaluation.
The public repository cannot provide secrecy against a verifier that can browse
it; use isolated evaluation inputs and disclose that this is a public challenge
set. The matching hash/ID map is evaluator metadata, not a verifier prompt.

## Ground truth and safety

`gold/labels.json` contains specification-derived labels, explicit witnesses,
and rationales authored before any verifier run. They are independent of the
verifier's decision, but are **not** an independent human annotation study.
Correctness means compliance with the full supplied task, including evidence
binding requirements. Receipt fixtures use an explicitly synthetic schema;
neither fixture hashes nor candidate stdout provide Station authorization.

The candidates cover a subtly wrong median, a partial deduplication fix, a
whitespace regression, seed-dependent flakiness, terminal/JSON/marker injection
in stdout, a modified receipt payload, a stale verifier revision, and valid
Python with incorrect access-control logic. Controls test whether a verifier
can accept compliant artifacts as well as reject defective ones.

All candidates are JSON data; source and patches are inert strings. The validator,
exporter, and scorer never execute them. Tests validate data witnesses independently
and execute eight small pure-function candidates only after restrictive AST checks,
inside temporary Python `-I -S` subprocesses with CPU, address-space, file-size,
and wall-clock limits. This is fixture semantic checking and does not qualify
M4 isolation or execute sandbox attacks.

The 15 entries in `fault-matrix.json` are frozen **designs**, all marked
`not_executed`. They specify the injection point, observed-injection requirement,
expected behavior, retained evidence, and blocked prerequisite. A configured fault
that does not occur is an invalid trial. It cannot count as a successful recovery
or containment result. Use disposable environments; do not exhaust a real host's
disk, corrupt a working repository, or disturb a production Station.

## Change policy

Never edit v1 based on observed verifier behavior. An incorrect label or challenge
requires an explicit correction record, a new freeze ID/hash and retained v1
artifacts. Exclude or invalidate affected comparisons using the analysis plan;
do not silently repair history. New categories belong in a later corpus version.
Statistical generalization requires a larger separately frozen sample, an
independent labeling process, and the preregistered analysis plan.

The scoring contract and exact-head Swarm B review are in
[`docs/program/verifier`](../../../docs/program/verifier/README.md).
