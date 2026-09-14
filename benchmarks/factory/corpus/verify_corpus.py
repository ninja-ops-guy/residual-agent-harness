from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from common import BENCHMARKS, CorpusManifest, host_evidence, report_entry  # noqa: E402
from residual.core import strict_json  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Verify a signed FB001-FB004 benchmark corpus")
    p.add_argument("corpus")
    p.add_argument("--require-current-host", action="store_true")
    args = p.parse_args()

    root = Path(args.corpus).resolve()
    manifest = CorpusManifest.from_dict(strict_json((root / "corpus-manifest.json").read_text(encoding="utf-8")))
    public_key = bytes.fromhex((root / "station-public-key.hex").read_text(encoding="ascii").strip())
    if not manifest.verify(public_key):
        raise SystemExit("corpus manifest signature invalid")
    if manifest.simulation:
        raise SystemExit("corpus contains simulated evidence")
    if args.require_current_host and host_evidence()["fingerprint"] != manifest.host["fingerprint"]:
        raise SystemExit("current host does not match corpus host fingerprint")

    checked = []
    for expected, bound in zip(BENCHMARKS, manifest.entries):
        workload = root / expected / "workload.json"
        report = root / expected / "results" / "comparison-report.json"
        entry = report_entry(expected, workload, report, public_key)
        if entry != bound:
            raise SystemExit(f"{expected} entry differs from signed manifest")
        if entry.simulation:
            raise SystemExit(f"{expected} is simulated")
        checked.append({"benchmark": expected, "workload_hash": entry.workload_hash,
                        "report_hash": entry.report_hash})

    print(json.dumps({"status": "valid", "manifest_hash": manifest.manifest_hash,
                      "source_commit": manifest.source_commit,
                      "model_name": manifest.model_name,
                      "model_version": manifest.model_version,
                      "host_fingerprint": manifest.host["fingerprint"],
                      "benchmarks": checked}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
