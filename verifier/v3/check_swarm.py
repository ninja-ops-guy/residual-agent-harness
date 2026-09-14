#!/usr/bin/env python3
"""verifier/v3 — 8-swarm execution acceptance checks.

Criteria:
 1. Track deliverable paths exist on merged main.
 2. Concurrent swarm work does not modify the canonical Factory M2-M4
    trust-boundary files relative to the ownership baseline.
 3. Full test suite passes.
 4. harness_specs verifier v2 still green.

The ownership baseline is intentionally explicit. When an authorized M2-M4
change is accepted (for example the canonical M4 merge), advance this baseline
in the same reviewed change so later swarm work cannot silently modify it.
"""
import os, subprocess, sys, json

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
BASELINE = "98c12f0"
OWNERSHIP_BASELINE = "412b66c35f7c0e1ac479fe60a5b7d33d5510e3af"
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

# Canonical Factory M2/M3 files plus the reserved M4 integration paths.
# Keep this exact rather than protecting all residual/factory/** so independent
# compiler/product work can continue without weakening runtime ownership.
PROTECTED_FILES = {
    "residual/factory/_sandbox_child.py",
    "residual/factory/evidence_bus.py",
    "residual/factory/evidence_receipts.py",
    "residual/factory/integrator.py",
    "residual/factory/runtime.py",
    "residual/factory/runtime_journal.py",
    "residual/factory/runtime_workspace.py",
    "residual/factory/scheduler.py",
    "residual/factory/station_issuer.py",
    "residual/factory/worker_contract.py",
}

failures = []

for p in REQUIRED_PATHS:
    if not os.path.exists(os.path.join(ROOT, p)):
        failures.append(f"missing deliverable path: {p}")

# Retain the broad change count from the original swarm baseline for reporting.
diff = subprocess.run(["git", "-C", ROOT, "diff", "--name-only", BASELINE, "HEAD"],
                      capture_output=True, text=True)
changed = diff.stdout.split()

ownership_diff = subprocess.run(
    ["git", "-C", ROOT, "diff", "--name-only", OWNERSHIP_BASELINE, "HEAD", "--", *sorted(PROTECTED_FILES)],
    capture_output=True, text=True,
)
if ownership_diff.returncode != 0:
    failures.append("unable to evaluate M2-M4 ownership diff")
else:
    protected_hits = [p for p in ownership_diff.stdout.split() if p in PROTECTED_FILES]
    if protected_hits:
        failures.append(
            "canonical Factory M2-M4 path modified without ownership-baseline advance: "
            + ", ".join(protected_hits)
        )

t = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                   cwd=ROOT, capture_output=True, text=True)
if t.returncode != 0:
    failures.append("pytest failed:\n" + t.stdout[-2000:])
test_summary = t.stdout.strip().splitlines()[-1] if t.stdout else "no output"

v2 = subprocess.run([sys.executable, "verifier/v2/check_specs.py"],
                    cwd=ROOT, capture_output=True, text=True)
if v2.returncode != 0:
    failures.append("verifier v2 regressed")

print(json.dumps({
    "changed_files": len(changed),
    "ownership_baseline": OWNERSHIP_BASELINE,
    "protected_files": len(PROTECTED_FILES),
    "pytest": test_summary,
}, indent=2))
if failures:
    print("FAIL:")
    for x in failures:
        print(" -", x)
    sys.exit(1)
print("PASS: 8-swarm acceptance checks green")
