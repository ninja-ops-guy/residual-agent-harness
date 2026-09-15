"""Reproduce narrow PR41 API findings from immutable local Git objects.

No network, model calls, branch writes or candidate execution. The exact trusted
VQ modules and core.py are materialized in a temporary namespace package; the
package initializer is omitted to avoid importing unrelated runtime modules.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


VQ_HEAD = "9dd0955afaf146719bcf9c8ff27d9dd14021fc4a"
M4_HEAD = "30d1d020469d958d90969bc02946145c248e0adb"
REPO = Path(__file__).resolve().parents[3]
CHILD = r'''
import json, sys, types
from pathlib import Path
package = types.ModuleType("residual")
package.__path__ = [str(Path(sys.argv[1]) / "residual")]
sys.modules["residual"] = package
from residual.vq.identity import VerifierIdentity
from residual.vq.outcomes import LabeledOutcome, LabelSource
from residual.vq.profile import VerifierQualityProfile
from residual.vq.frozen import FrozenWorkloadFixture, FixtureCase
from residual.vq.benchmark import VerifierBenchmark
identity = VerifierIdentity.build("exact-head-probe", "synthetic", {}, {})
fixture = FrozenWorkloadFixture("synthetic-api-probe", (
    FixtureCase("known-good", {"answer": 1}, True),
    FixtureCase("known-defect", {"answer": 0}, False)))
probe = {}
for status in ("unknown", "error", "fail"):
    report = VerifierBenchmark(min_samples=1).run(
        lambda artifact: status, identity, fixture, repo_dir=sys.argv[1], safety_critical=False)
    probe["string_status_" + status] = {
        "verdicts": [o["verdict"] for o in report.raw_labeled_outcomes],
        "coverage": report.profile["coverage"],
        "false_accept": report.profile["false_accept"]}
def broken(artifact):
    raise TimeoutError("synthetic unavailable verifier")
try:
    VerifierBenchmark().run(broken, identity, fixture, repo_dir=sys.argv[1])
except Exception as exc:
    probe["verifier_exception"] = {"escaped_exception": type(exc).__name__, "report_returned": False}
rows = [(True, True), (True, True), (True, False),
        (False, False), (False, False), (False, False), (False, True)]
outcomes = [LabeledOutcome(str(i), identity.name, verdict, truth, LabelSource.INDEPENDENT_AUDIT)
            for i, (verdict, truth) in enumerate(rows)]
profile = VerifierQualityProfile.from_outcomes(identity, outcomes, min_samples=1)
probe["class_orientation"] = {"TA": 2, "FA": 1, "TR": 3, "FR": 1,
    "reported_recall": profile.recall.estimate,
    "acceptance_recall": 2 / 3, "defect_recall": 3 / 4}
coerced = VerifierBenchmark.recompute_from_outcomes(identity, [{
    "case_id": "malformed-bools", "verifier_id": identity.name,
    "verdict": "false", "ground_truth": "false", "label_source": "independent_audit"
}], min_samples=1)
probe["string_false_replay"] = {"precision": coerced["profile"]["precision"],
                                "false_accept": coerced["profile"]["false_accept"]}
print(json.dumps(probe, sort_keys=True, indent=2))
'''


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True,
                          capture_output=True, timeout=10).stdout


def main() -> None:
    paths = git("ls-tree", "-r", "--name-only", VQ_HEAD, "residual/vq").decode().splitlines()
    paths.append("residual/core.py")
    sources = {}
    with tempfile.TemporaryDirectory(prefix="residual-vq-probe-") as temp:
        root = Path(temp)
        for name in paths:
            if not name.endswith(".py"):
                continue
            data = git("show", f"{VQ_HEAD}:{name}")
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            sources[name] = {"commit": VQ_HEAD,
                             "git_blob": git("rev-parse", f"{VQ_HEAD}:{name}").decode().strip(),
                             "sha256": hashlib.sha256(data).hexdigest()}
        for name in ("residual/factory/m4_sandbox.py", "residual/factory/m4_integrator.py"):
            data = git("show", f"{M4_HEAD}:{name}")
            sources[name] = {"commit": M4_HEAD,
                             "git_blob": git("rev-parse", f"{M4_HEAD}:{name}").decode().strip(),
                             "sha256": hashlib.sha256(data).hexdigest()}
        script = root / "probe.py"
        script.write_text(CHILD)
        result = subprocess.run([sys.executable, "-I", "-S", str(script), str(root)],
                                cwd=root, capture_output=True, check=True, text=True, timeout=20)
    report = {"schema": "residual.preflight.vq-head-audit.v1", "vq_pr": 41, "vq_head": VQ_HEAD,
              "m4_pr": 81, "m4_head": M4_HEAD, "baseline_head": git("rev-parse", "HEAD").decode().strip(),
              "scope": "synthetic_API_probes_and_read_only_M4_source_review",
              "sources": sources, "probes": json.loads(result.stdout)}
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
