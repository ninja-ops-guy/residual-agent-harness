# Application preparation fixtures

Run from the checkout root:

```sh
python scripts/application_preflight.py --output runs/application-preflight.json
```

The output file must not already exist. No provider credentials are needed.

Six independent public toy tasks cover code repair, configuration generation,
documentation synthesis, security triage, test generation and data cleaning.
Each includes a correct candidate, a broken candidate and missing output.
The runner uses the actual `RequirementCompiler`, `ExecutionPlan` and
`WorkerContract` classes, binds each contract to the plan, and evaluates those
three candidates with a deliberately narrow independent fixture oracle.

Supplied code, patches and tests are inert data. These examples demonstrate
preparation and assessment across application types. They do not demonstrate
general semantic verification, model execution, OS isolation, receipt publication,
M4 integration or deployment. Every report states `development_fixture`, zero
model calls and `station_acceptance: NOT_REQUESTED`.

The JSON fixtures are hash-locked by `manifest.json`. Keep them out of the
confirmatory workload and out of model-selection decisions. A changed fixture
requires a reviewed manifest revision; these public cases are never held-out
paper evidence. The manifest detects accidental content changes relative to its
anchor; it does not authenticate a maliciously replaced manifest.
