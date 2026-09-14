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

This repairs PR #50 and depends on #61's lifecycle restoration followed by the
ownership gate transition in #59. Neither Factory source nor baseline is changed
in this packaging diff. Requalify after retargeting each parent to main. Issue
#48 remains open for requirement-by-requirement status reconciliation. The
parent source includes #58's receipt-backed M4 planning, not a claim of full M4
integration or Factory EVAL completion (#22/#60/#26). A successful package import
does not certify those requirements.
