from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from residual.core import ContractError, digest
from residual.discovery_metrics import MetricRegistry, admission_binding, load_metric_registry
from residual.receipts import StationReceipt
from residual.verifier import CheckResult


SNAPSHOT_HASH = "7a239febb03972fcc6e89d205cfa83276fd484e24d2e70b46b4229115addcd2a"


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry",default="residual/discovery_metric_registry.json")
    ap.add_argument("--output",default="runs/m6-spec-007s/evidence.json")
    a=ap.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)

    registry=load_metric_registry(a.registry)
    rules={"experiment":"M6-SPEC-007S","rules":"registry-binding-control-v1"}
    proposal={"type":"control","metric":"mean_wall_clock_s","value":696.4382}
    binding=admission_binding(
        evidence_snapshot_hash=SNAPSHOT_HASH,registry=registry,verifier_rules=rules
    )
    receipt=StationReceipt(
        task_id="m6-registry-binding-control",
        cache_key=binding["cache_key"],
        value_hash=digest(proposal),
        verifier_name="m6:admission",
        verifier_revision=binding["verifier_revision"],
        verdict=CheckResult.PASS,
        engine_name="residual-m6",
        engine_version="007s",
    )
    baseline_matches=receipt.matches(
        value=proposal,cache_key=binding["cache_key"],
        verifier_name="m6:admission",verifier_revision=binding["verifier_revision"],
        parents=(),engine_name="residual-m6",engine_version="007s",
    )

    changed=[]
    for d in registry.definitions:
        if d.metric_id=="mean_wall_clock_s":
            changed.append(replace(
                d,
                population="Retained M6 runs whose bound cohort_id equals altered-population-v2.",
                collection_method=(
                    "Filter retained runs to cohort_id == altered-population-v2 and "
                    "compute arithmetic_mean(wall_clock_s)."
                ),
            ))
        else:
            changed.append(d)
    altered=MetricRegistry(registry.revision,changed)
    altered_binding=admission_binding(
        evidence_snapshot_hash=SNAPSHOT_HASH,registry=altered,verifier_rules=rules
    )
    altered_matches=receipt.matches(
        value=proposal,cache_key=altered_binding["cache_key"],
        verifier_name="m6:admission",verifier_revision=altered_binding["verifier_revision"],
        parents=(),engine_name="residual-m6",engine_version="007s",
    )

    snapshot=registry.bind_snapshot({"mean_wall_clock_s":696.4382})
    tampered=dict(snapshot,metric_registry_sha256="f"*64)
    tamper_rejected=False
    try:
        registry.validate_snapshot_binding(tampered)
    except ContractError:
        tamper_rejected=True

    unit_rejected=False
    try:
        registry.validate_observation("mean_wall_clock_s",696.4382,"milliseconds")
    except ContractError:
        unit_rejected=True

    passed=all([
        baseline_matches,
        registry.registry_sha256 != altered.registry_sha256,
        binding["cache_key"] != altered_binding["cache_key"],
        binding["verifier_revision"] != altered_binding["verifier_revision"],
        not altered_matches,
        tamper_rejected,
        unit_rejected,
    ])
    evidence={
        "schema_version":1,
        "experiment":"M6-SPEC-007S",
        "pass":passed,
        "baseline_registry_sha256":registry.registry_sha256,
        "altered_registry_sha256":altered.registry_sha256,
        "baseline_receipt":receipt.to_dict(),
        "controls":{
            "baseline_receipt_matches":baseline_matches,
            "semantic_change_changes_registry_hash":registry.registry_sha256 != altered.registry_sha256,
            "semantic_change_changes_cache_key":binding["cache_key"] != altered_binding["cache_key"],
            "semantic_change_changes_verifier_revision":binding["verifier_revision"] != altered_binding["verifier_revision"],
            "old_receipt_rejected_under_altered_registry":not altered_matches,
            "snapshot_registry_hash_tamper_rejected":tamper_rejected,
            "unit_mismatch_rejected":unit_rejected,
        },
        "authority":{"register_metric":False,"implement_candidate":False,"promote":False},
    }
    out.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print("M6_SPEC_007S_EVIDENCE="+json.dumps(evidence,sort_keys=True,separators=(",",":")))
    return 0 if passed else 1


if __name__=="__main__":
    raise SystemExit(main())
