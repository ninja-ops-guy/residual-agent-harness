# Clean-install qualification

The Python 3.11/3.12/3.13 matrix separates two claims and two fresh environments.

**Installed wheel:** build one wheel, retain its SHA-256 and source commit/tree,
install that wheel with `factory,marketplace` extras (without test tools), and run
`pip check`. From a temporary directory outside the checkout, run the smoke
script using `python -I` with `PYTHONPATH` and `PYTHONHOME` removed. Imported
Residual, provider, and observation modules must resolve to recorded distribution
files inside the venv, not to the checkout. Station UI/schema assets and all four
installed console scripts must be present and usable. Preserve JSON results,
logs, dependency versions, and the tested wheel even when qualification fails.

**Source qualification:** a different venv installs
`.[factory,marketplace,test]`. Run traceability, the executable module tutorial,
the scripted onboarding demo, and the full v3 gate (which invokes pytest and v2).
Checkout uses full history so the fail-closed ownership baselines are available.
Source checks are not substituted for the installed-wheel smoke test.

PyYAML remains in the existing Factory extra and is also declared in `test`;
pytest is test-only. No core runtime dependency is added merely to run a
repository development script. The smoke is not a live provider, OS-isolation,
Factory M4/EVAL, benchmark, or production qualification.

This is the clean-install successor to stale PR #50. It is stacked on #69, whose
base is the exact reviewed M2+M4 integration commit `9aa29001c7bb5fc533ae3524017c9b4efdaed837`.
The source therefore includes the current-main M2 lifecycle repair and the M4
accepted-state safety repair, plus the rebuilt ownership gate. This qualification
must still be reconciled and rerun after #68/#66/#69 are actually merged to
`main`; the synthetic integration ancestry is review evidence, not a substitute
for the final merged tree.

A successful package/import qualification does not make the trusted-fixture M4
lane an OS sandbox, does not close issue #63, and does not authorize measured
benchmark claims from #67 or the older benchmark stack. The definitive
black-and-green Pages presentation is unrelated and unchanged.
