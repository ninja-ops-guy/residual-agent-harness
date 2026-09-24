#!/usr/bin/env python3
"""Paper artifact pipeline for EXP-M6-SLM.

Exports, from the append-only results store (see results_store.py):

  - experiment manifests (one JSON per run, content-addressed)
  - result tables (CSV and markdown) using the frozen metric names
  - reproducibility metadata (store head digest, record count, schema
    version, protocol version) sufficient to locate every artifact

Boundary: this reads only the research results store. It never touches
production logs, holdout labels, or benchmark items.

CLI:
  python paper_export.py --help
  python paper_export.py manifest --store runs.jsonl --outdir out/
  python paper_export.py table --store runs.jsonl --format csv
  python paper_export.py table --store runs.jsonl --format markdown
  python paper_export.py repro --store runs.jsonl
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from typing import Dict, List, Optional, Sequence

from results_store import (
    CONDITIONS,
    KNOWN_METRICS,
    SCHEMA_VERSION,
    iter_records,
    verify_chain,
)

PROTOCOL_VERSION = "eval-protocol-v1.0.0"
METRIC_ORDER = sorted(KNOWN_METRICS)


def _load_verified(store: str) -> List[Dict[str, object]]:
    violations = verify_chain(store)
    if violations:
        raise ValueError(
            "refusing to export from a store with chain violations: %s"
            % "; ".join(violations)
        )
    return list(iter_records(store))


def export_manifests(records: List[Dict[str, object]], outdir: str) -> List[str]:
    """Write one content-addressed manifest JSON per run."""
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for rec in records:
        body = json.dumps(rec, sort_keys=True, indent=2)
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        path = os.path.join(
            outdir, "manifest-%s-%s.json" % (rec["run_id"], digest[:12])
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body + "\n")
        paths.append(path)
    return paths


def result_table(records: List[Dict[str, object]], fmt: str) -> str:
    """Render a result table (csv|markdown) over frozen metric names.

    Rows are runs; columns are run_id, harness_condition, seed_index,
    then only the metrics present in at least one record.
    """
    present = [
        m for m in METRIC_ORDER
        if any(m in rec.get("metrics", {}) for rec in records)
    ]
    header = ["run_id", "harness_condition", "seed_index"] + present
    rows = []
    for rec in records:
        metrics = rec.get("metrics", {})
        rows.append(
            [
                str(rec.get("run_id", "")),
                str(rec.get("harness_condition", "")),
                str(rec.get("seed_index", "")),
            ]
            + [str(metrics.get(m, "")) for m in present]
        )
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        writer.writerows(rows)
        return buf.getvalue().rstrip("\r\n")
    # markdown
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def reproducibility_metadata(records: List[Dict[str, object]]) -> Dict[str, object]:
    """Metadata needed to locate and re-verify every exported artifact."""
    head = records[-1]["digest"] if records else None
    return {
        "store_schema_version": SCHEMA_VERSION,
        "evaluation_protocol": PROTOCOL_VERSION,
        "record_count": len(records),
        "head_digest": head,
        "conditions_present": sorted(
            {r.get("harness_condition") for r in records}
            & set(CONDITIONS)
        ),
        "run_ids": [r.get("run_id") for r in records],
        "boundary": (
            "research results store only; no production logs, no holdout "
            "labels, no benchmark items"
        ),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--store", required=True, help="path to the JSONL results store"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    man = sub.add_parser("manifest", help="export per-run manifests")
    man.add_argument("--outdir", required=True)
    tab = sub.add_parser("table", help="export a result table")
    tab.add_argument("--format", choices=("csv", "markdown"),
                     default="markdown")
    tab.add_argument("--output", help="default: stdout")
    sub.add_parser("repro", help="print reproducibility metadata")
    args = parser.parse_args(argv)

    try:
        records = _load_verified(args.store)
        if args.command == "manifest":
            for path in export_manifests(records, args.outdir):
                print(path)
        elif args.command == "table":
            text = result_table(records, args.format)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as fh:
                    fh.write(text + "\n")
            else:
                print(text)
        else:
            print(json.dumps(reproducibility_metadata(records), indent=2,
                             sort_keys=True))
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
