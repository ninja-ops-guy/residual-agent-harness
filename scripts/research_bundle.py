#!/usr/bin/env python3
"""Freeze and verify research evidence without model credentials."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from residual.research_bundle import MetricSpec, ResearchBundleError, freeze_bundle, load_spec, render_metric_table, verify_bundle

def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def freeze(args):
    spec = load_spec(args.spec); metrics = [MetricSpec.from_mapping(v) for v in spec.get("metrics", [])]
    manifest = freeze_bundle(args.root, experiment_id=spec.get("experiment_id", ""), source_commit=spec.get("source_commit", ""), artifacts=spec.get("artifacts", []), metrics=metrics, metadata=spec.get("metadata", {}))
    _write_json(Path(args.manifest), manifest)
    if args.table:
        table = Path(args.table); table.parent.mkdir(parents=True, exist_ok=True); table.write_text(render_metric_table(manifest), encoding="utf-8")
    print(json.dumps({"status": "frozen", "bundle_sha256": manifest["bundle_sha256"]}, sort_keys=True)); return 0

def verify(args):
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8")); receipt = verify_bundle(args.root, manifest)
    if args.table and Path(args.table).read_text(encoding="utf-8") != render_metric_table(manifest): raise ResearchBundleError("rendered metric table drifted from frozen manifest")
    print(json.dumps(receipt, sort_keys=True)); return 0

def main(argv=None):
    parser = argparse.ArgumentParser(description="Freeze/verify source-bound research evidence bundles"); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("freeze"); p.add_argument("--root", required=True); p.add_argument("--spec", required=True); p.add_argument("--manifest", required=True); p.add_argument("--table"); p.set_defaults(func=freeze)
    p = sub.add_parser("verify"); p.add_argument("--root", required=True); p.add_argument("--manifest", required=True); p.add_argument("--table"); p.set_defaults(func=verify)
    args = parser.parse_args(argv)
    try: return args.func(args)
    except (ResearchBundleError, OSError, json.JSONDecodeError) as exc: parser.error(str(exc)); return 2
if __name__ == "__main__": raise SystemExit(main())
