"""CLI for EXP-NESTED-SWARM-001 evidence preparation and paper-ready JSON export."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from residual.core import canonical, strict_json
from .nested_swarm import TrialRecord, build_manifest, summarize_experiment

def main(argv=None):
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    m=sub.add_parser("manifest"); m.add_argument("--registered-at",required=True); m.add_argument("--corpus-sha256",required=True); m.add_argument("--runtime-revision",required=True); m.add_argument("--trials",type=int,default=3); m.add_argument("--output",type=Path,required=True)
    r=sub.add_parser("report"); r.add_argument("--manifest",type=Path,required=True); r.add_argument("--trials-dir",type=Path,required=True); r.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    if a.command=="manifest":
        x=build_manifest(registered_at=a.registered_at,task_corpus_sha256=a.corpus_sha256,runtime_revision=a.runtime_revision,trials_per_arm=a.trials)
        a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(canonical(x.payload()|{"sha256":x.sha256})+"\n"); return 0
    raw=strict_json(a.manifest.read_text()); raw.pop("sha256",None)
    from .nested_swarm import ExperimentArm, ExperimentManifest
    raw["arms"]=tuple(ExperimentArm(**{**x,"provider_kinds":tuple(x["provider_kinds"])}) for x in raw["arms"]); raw["hypotheses"]=tuple(raw["hypotheses"]); raw["secondary_metrics"]=tuple(raw["secondary_metrics"])
    manifest=ExperimentManifest(**raw); trials=[]
    for path in sorted(a.trials_dir.glob("*.json")):
        x=strict_json(path.read_text()); expected=x.pop("sha256",None); t=TrialRecord(**x)
        if expected!=t.sha256: raise ValueError(f"trial hash mismatch: {path.name}")
        trials.append(t)
    report=summarize_experiment(manifest,trials); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(canonical(report)+"\n"); return 0

if __name__=="__main__": raise SystemExit(main())
