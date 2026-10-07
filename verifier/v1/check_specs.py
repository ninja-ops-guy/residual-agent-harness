#!/usr/bin/env python3
"""verifier/v1 — Spec-set completeness checks for residual-agent-harness.

Acceptance criteria:
 1. All 17 expected files present in harness_specs/ (16 docs + README).
 2. No incomplete markers (TODO/TBD/FIXME/placeholder/"to be written").
 3. PATH_TO_10_SPECS.md: N9-R1..N9-R28 contiguous (28 reqs),
    T10-R1..T10-R20 contiguous (20 reqs).
 4. Every *-R<n> requirement family in every spec doc is contiguous
    from R1 to R-max (no gaps).
 5. Every spec doc declares RFC 2119 normative language or is a
    non-normative doc (assessment/diagrams/conflict resolutions).
"""
import re, sys, os, json

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
SPEC_DIR = os.path.join(ROOT, "harness_specs")

EXPECTED = [
    "README.md", "DESIGN.md", "SPECS.md", "GAP_ANALYSIS.md",
    "NETOPS_SECOPS_SPECS.md", "WORLD_CLASS_SPECS.md", "V040_ASSESSMENT.md",
    "GAP_CLOSURE_SPECS.md", "PHASE_4_5_SPECS.md", "RESILIENCE_SPECS.md",
    "MESH_SPECS.md", "STUDIO_SPECS.md", "M2_M3_M4_SPECS.md",
    "CONTROL_PLANE_SPECS.md", "PATH_TO_10_SPECS.md",
    "CONFLICT_RESOLUTIONS.md", "ARCHITECTURE_DIAGRAMS.md",
]
NON_NORMATIVE = {"V040_ASSESSMENT.md", "ARCHITECTURE_DIAGRAMS.md",
                 "CONFLICT_RESOLUTIONS.md", "GAP_ANALYSIS.md", "README.md"}
BAD_MARKERS = re.compile(r"\b(TODO|TBD|FIXME|placeholder|to be written)\b", re.I)
REQ_RE = re.compile(r"\*\*([A-Z0-9]+(?:-[A-Z0-9]+)*)-R(\d+)\.\*\*")

failures, results = [], {}

# 1. presence
missing = [f for f in EXPECTED if not os.path.isfile(os.path.join(SPEC_DIR, f))]
if missing:
    failures.append(f"missing files: {missing}")
results["files_present"] = len(EXPECTED) - len(missing)

# 2. markers
for f in EXPECTED:
    p = os.path.join(SPEC_DIR, f)
    if not os.path.isfile(p):
        continue
    text = open(p, encoding="utf-8").read()
    hits = BAD_MARKERS.findall(text)
    if hits:
        failures.append(f"{f}: incomplete markers {sorted(set(hits))}")

# 3+4. requirement contiguity
for f in EXPECTED:
    p = os.path.join(SPEC_DIR, f)
    if not os.path.isfile(p):
        continue
    text = open(p, encoding="utf-8").read()
    fams = {}
    for fam, n in REQ_RE.findall(text):
        fams.setdefault(fam, set()).add(int(n))
    for fam, nums in fams.items():
        expected = set(range(1, max(nums) + 1))
        if nums != expected:
            failures.append(f"{f}: {fam} non-contiguous, missing {sorted(expected - nums)}")
    if f == "PATH_TO_10_SPECS.md":
        n9 = fams.get("N9", set()); t10 = fams.get("T10", set())
        if len(n9) != 28:
            failures.append(f"PATH_TO_10: N9 count {len(n9)} != 28")
        if len(t10) != 20:
            failures.append(f"PATH_TO_10: T10 count {len(t10)} != 20")
        results["N9_requirements"] = len(n9)
        results["T10_requirements"] = len(t10)

# 5. RFC 2119 declaration
for f in EXPECTED:
    if f in NON_NORMATIVE:
        continue
    p = os.path.join(SPEC_DIR, f)
    if not os.path.isfile(p):
        continue
    if "RFC 2119" not in open(p, encoding="utf-8").read():
        failures.append(f"{f}: missing RFC 2119 declaration")

print(json.dumps(results, indent=2))
if failures:
    print("FAIL:")
    for x in failures:
        print(" -", x)
    sys.exit(1)
print("PASS: all spec-set completeness checks green")
