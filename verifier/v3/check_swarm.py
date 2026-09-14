#!/usr/bin/env python3
"""verifier/v3 — 8-swarm execution acceptance checks.

Criteria:
 1. Track deliverable paths exist on merged main.
 2. No modifications to M2-M4-owned paths (residual/swarm, evidence,
    scheduler, integrator) relative to baseline commit 98c12f0.
 3. Full test suite passes.
 4. harness_specs verifier v2 still green.
"""
import os, subprocess, sys, json

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
BASELINE = "98c12f0"
REQUIRED_PATHS = [
    "implementation-status.yaml", "scripts/status_check.py",
    "docs/status/IMPLEMENTATION_STATUS.md",
    "residual/sandbox", "tests/redteam",
    "residual/cluster",
    "residual/orchestrator",
    "residual/eval", "residual/soak",
    "residual/gateway", "residual/lifecycle_glue",
    "residual/crypto", "residual/connectors/conformance",
    "residual/studio_frontend", "examples/onboarding",
]
PROTECTED = ["residual/swarm", "residual/evidence", "residual/scheduler", "residual/integrator"]

failures = []

for p in REQUIRED_PATHS:
    if not os.path.exists(os.path.join(ROOT, p)):
        failures.append(f"missing deliverable path: {p}")

diff = subprocess.run(["git", "-C", ROOT, "diff", "--name-only", BASELINE, "HEAD"],
                      capture_output=True, text=True)
changed = diff.stdout.split()
for p in PROTECTED:
    hits = [c for c in changed if c.startswith(p + "/")]
    if hits:
        failures.append(f"protected path modified: {p} ({len(hits)} files)")

t = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                   cwd=ROOT, capture_output=True, text=True)
if t.returncode != 0:
    failures.append("pytest failed:\n" + t.stdout[-2000:])
test_summary = t.stdout.strip().splitlines()[-1] if t.stdout else "no output"

v2 = subprocess.run([sys.executable, "verifier/v2/check_specs.py"],
                    cwd=ROOT, capture_output=True, text=True)
if v2.returncode != 0:
    failures.append("verifier v2 regressed")

print(json.dumps({"changed_files": len(changed), "pytest": test_summary}, indent=2))
if failures:
    print("FAIL:")
    for x in failures:
        print(" -", x)
    sys.exit(1)
print("PASS: 8-swarm acceptance checks green")
