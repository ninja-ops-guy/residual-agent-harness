#!/usr/bin/env python3
"""Create empty paper templates; never read outcomes or invoke providers.

This is deliberately not an inferential analysis or experiment launcher.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments/preflight/science/protocol.v1.json"
PAIR_FIELDS = ["family_id", "task_id", "repeat_index", "configuration", "model_class", "topology"]
PROVENANCE = ["protocol_sha256", "bundle_sha256", "analysis_sha256"]

# Columns are data contracts, not simulated observations.
PLOTS = {
    "reliability_curve": {
        "title": "R0–R5 reliability and useful acceptance",
        "x": "configuration", "y": "rate", "y_label": "Rate (with denominator)",
        "categories": ["R0", "R1", "R2", "R3", "R4", "R5"],
        "columns": ["configuration", "metric", "estimate", "ci_low", "ci_high", "numerator", "denominator", "unknown", "ci_status"],
    },
    "acceptance_correctness": {
        "title": "Acceptance and independent correctness",
        "x": "acceptance", "y": "correctness", "y_label": "Independent grade",
        "categories": ["accepted", "rejected", "unknown"],
        "columns": ["configuration", "acceptance", "independent_grade", "count", "scheduled_n"],
    },
    "reliability_cost_pareto": {
        "title": "Reliability, useful acceptance and cost",
        "x": "total_cost_usd", "y": "accepted_error_rate", "y_label": "Accepted error rate",
        "columns": ["configuration", "model_class", "topology", "total_cost_usd", "accepted_error_rate", "aer_lower_bound", "aer_upper_bound", "verified_goodput", "acceptance_rate", "latency_seconds", "cost_complete", "dominance_status"],
    },
    "model_degradation": {
        "title": "Frozen capacity classes: raw and accepted outcomes",
        "x": "model_class", "y": "rate", "y_label": "Rate (with denominator)",
        "categories": ["S", "M", "W", "L"],
        "columns": ["model_class", "model_identity", "configuration", "metric", "estimate", "ci_low", "ci_high", "numerator", "denominator", "unknown"],
    },
    "orchestration_tax": {
        "title": "Predicted and observed orchestration tax",
        "x": "predicted_tax", "y": "observed_tax", "y_label": "Observed tax (declared unit)",
        "columns": PAIR_FIELDS + ["predicted_tax", "observed_tax", "tax_unit", "single_worker_cost", "swarm_cost", "selected_topology", "controller_revision"],
    },
    "verifier_roc": {
        "title": "Verifier defect detection: decision coverage shown separately",
        "x": "false_positive_rate", "y": "true_positive_rate", "y_label": "Defect-detection true-positive rate",
        "columns": ["verifier_revision", "corpus_sha256", "threshold", "true_positive_rate", "false_positive_rate", "decision_coverage", "tp", "fp", "tn", "fn", "unknown", "execution_error"],
    },
    "verifier_calibration": {
        "title": "Verifier confidence calibration",
        "x": "mean_predicted_defect_probability", "y": "observed_defect_rate", "y_label": "Independently labeled defect rate",
        "columns": ["verifier_revision", "corpus_sha256", "bin_lower", "bin_upper", "mean_predicted_defect_probability", "observed_defect_rate", "count", "unknown", "execution_error"],
    },
    "soak_failure": {
        "title": "Soak survival with at-risk and censoring counts",
        "x": "elapsed_hours", "y": "survival_probability", "y_label": "Survival probability",
        "columns": ["cohort_id", "elapsed_hours", "at_risk", "failures", "censored", "survival_probability", "ci_low", "ci_high", "failure_definition_revision"],
    },
}

TABLES = {
    "paired_cells": PROVENANCE + ["cell_id"] + PAIR_FIELDS + ["execution_status", "acceptance_status", "raw_grade", "accepted_grade", "verifier_status", "elapsed_seconds", "cost_usd", "usage_complete"],
    "hypothesis_results": PROVENANCE + ["hypothesis_id", "contrast", "endpoint", "effect_pp", "ci95_low", "ci95_high", "ci9875_low", "ci9875_high", "raw_p", "holm_p", "inference_status", "family_count"],
    "competitive_comparison": ["target", "version", "criterion", "status", "implementation_kind", "primary_source_url", "source_sha256", "code_permalink", "configuration_sha256", "reproduction_command", "artifact_sha256", "reviewer", "review_date", "limitations", "disagreement"],
    "claim_evidence": ["claim_id", "claim_text", "category", "protocol_sha256", "bundle_sha256", "analysis_sha256", "evidence_path", "status", "limitations"],
    "missingness": PROVENANCE + ["configuration", "scheduled_n", "missing_cell_count", "acceptance_unknown", "grade_unknown", "usage_unknown", "timing_unknown", "corrupt_artifact_count"],
}

DIAGRAM = """# Evidence pipeline (architecture template; no execution claimed)

```mermaid
flowchart TD
  W["Frozen workload cell"] --> P["Execution plan"]
  P --> C["Worker contract"]
  C --> R["Worker receipts and candidate tree"]
  V["Verifier revision and policy"] --> E["Verification outputs"]
  R --> E
  E --> I["Integration receipt and accepted tree"]
  I --> B["Retained artifact bundle"]
  W --> B
  B --> M["Offline metrics and claim ledger"]
```

Every arrow is a required hash-bound reference to audit, not proof of an
implemented edge. Independent grades and the externally retained bundle digest
must accompany the reconstruction. Metrics do not write accepted state.
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protocol(protocol: dict) -> None:
    """Validate the preparation contract, including deliberately blocked launch."""
    if protocol.get("schema_version") != "residual.science-preparation.v1":
        raise ValueError("unsupported science preparation version")
    if protocol.get("status") != "preparation_frozen_launch_blocked":
        raise ValueError("this preparation tool cannot qualify a launch")
    if protocol.get("confirmatory_launch_enabled") is not False:
        raise ValueError("confirmatory launch must remain disabled")
    if protocol.get("result_access") != "no_confirmatory_outcomes_collected_by_this_lane":
        raise ValueError("outcome-access declaration changed")
    if protocol.get("pair_fields") != PAIR_FIELDS:
        raise ValueError("paired identity contract changed")
    if protocol.get("repetitions") != 10:
        raise ValueError("repetition policy changed")
    inference = protocol.get("inference", {})
    expected = [
        ("H01", "R4", "R0", "accepted_error_rate"),
        ("H02", "R4", "R0", "verified_goodput"),
        ("H03", "R5", "R4", "accepted_error_rate"),
        ("H04", "R5", "R4", "verified_goodput"),
    ]
    found = [(h.get("id"), h.get("treatment"), h.get("control"), h.get("endpoint")) for h in inference.get("holm_family", [])]
    if found != expected or inference.get("alpha") != 0.05 or inference.get("unavailable_p") != 1:
        raise ValueError("fixed Holm family changed")
    if inference.get("bootstrap_draws") != 20000 or inference.get("swap_draws") != 99999:
        raise ValueError("resampling contract changed")
    if protocol.get("templates") != list(PLOTS):
        raise ValueError("template contract changed")
    if protocol.get("launch_gates") is None or any(g.get("status") != "unresolved" for g in protocol["launch_gates"]):
        raise ValueError("preparation cannot certify launch gates")
    gates = {g.get("id") for g in protocol["launch_gates"]}
    if not {"m4_qualification", "heldout_workload", "model_resolution", "paired_inference", "power_design", "external_commitment"} <= gates:
        raise ValueError("required launch gate missing")
    if protocol.get("missingness", {}).get("drop_scheduled_cells") is not False:
        raise ValueError("scheduled cells cannot be excluded")
    if protocol.get("missingness", {}).get("unknown_is_pass") is not False:
        raise ValueError("UNKNOWN cannot become PASS")
    if protocol.get("degradation", {}).get("model_classes") != ["S", "M", "W", "L"]:
        raise ValueError("frozen capacity classes changed")
    routes = protocol.get("heterogeneous_routes", [])
    if [(r.get("id"), r.get("coordinator"), r.get("workers"), r.get("reviewer")) for r in routes] != [
        ("H0", "S", ["S"] * 4, "S"), ("H1", "S", ["W"] * 4, "S"),
        ("H2", "W", ["W"] * 4, "S"), ("H3", "L", ["L"] * 4, "S"),
    ]:
        raise ValueError("heterogeneous route matrix changed")


def load_protocol(path: Path = PROTOCOL) -> tuple[dict, str]:
    expected = path.with_suffix(".sha256").read_text(encoding="utf-8").split()
    if len(expected) != 2 or expected[1] != path.name or expected[0] != digest(path):
        raise ValueError("protocol byte commitment mismatch")
    protocol = json.loads(path.read_text(encoding="utf-8"))
    validate_protocol(protocol)
    return protocol, expected[0]


def render_plot(path: Path, spec: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with plt.rc_context({"svg.hashsalt": "residual-empty-paper-v1", "svg.fonttype": "none", "font.family": "DejaVu Sans"}):
        fig, ax = plt.subplots(figsize=(7.2, 4.8), layout="constrained")
        ax.set_title(spec["title"], fontsize=11, pad=18)
        ax.set_xlabel(spec["x"].replace("_", " "))
        ax.set_ylabel(spec["y_label"])
        categories = spec.get("categories")
        if categories:
            ax.set_xticks(range(len(categories)), categories)
            ax.set_xlim(-0.5, len(categories) - 0.5)
        if spec["y"] == "correctness":
            ax.set_yticks([0, 1, 2], ["correct", "incorrect", "unknown"])
            ax.set_ylim(-0.5, 2.5)
        elif spec["y"] in {"rate", "accepted_error_rate", "true_positive_rate", "observed_defect_rate", "survival_probability"}:
            ax.set_ylim(0, 1)
        ax.text(0.5, 0.52, "NO RESULTS — TEMPLATE", transform=ax.transAxes,
                ha="center", va="center", fontsize=13, color="#4b5563",
                bbox={"facecolor": "white", "edgecolor": "#9ca3af", "pad": 12})
        ax.text(0.5, 0.35, "Empty axes are not observations", transform=ax.transAxes,
                ha="center", color="#6b7280", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        fig.savefig(path, metadata={"Date": None, "Creator": "Residual paper template generator"})
        plt.close(fig)
        if path.suffix == ".svg":
            path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")


def generate(output: Path, protocol_path: Path = PROTOCOL, render: bool = False) -> dict:
    _, protocol_sha = load_protocol(protocol_path)
    # Refuse to mix templates with retained results or overwrite prior artifacts.
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    for name, spec in PLOTS.items():
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, lineterminator="\n").writerow(PROVENANCE + spec["columns"])
        payload = {"schema_version": "residual.paper-template.v1", "evidence_level": "empty_template",
                   "protocol_sha256": protocol_sha, "plot_id": name, **spec, "data": []}
        (output / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if render:
            render_plot(output / f"{name}.svg", spec)
    for name, columns in TABLES.items():
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, lineterminator="\n").writerow(columns)
    (output / "evidence_pipeline.md").write_text(DIAGRAM, encoding="utf-8")
    (output / "README.md").write_text(
        "# Empty paper templates\n\nNo results or synthetic observations are present.\n"
        "CSV files contain headers only; plot JSON data arrays are empty.\n"
        "ROC positive class is independently labeled defect. UNKNOWN and execution errors\n"
        "are separate coverage counts, not false positives/negatives. A verifier without\n"
        "a meaningful pre-frozen score has one operating point, not an invented ROC.\n"
        "Calibration bins are [0,.1), ... [.9,1]; no post-result adaptive bins.\n"
        "Figure generation is not the paired inferential implementation.\n", encoding="utf-8")
    manifest = {"schema_version": "residual.paper-template-manifest.v1", "evidence_level": "empty_template",
                "protocol_sha256": protocol_sha, "row_count": 0,
                "files": {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--render", action="store_true", help="render empty SVG axes using Matplotlib")
    args = parser.parse_args()
    manifest = generate(args.output, args.protocol, args.render)
    print(json.dumps({"output": str(args.output), "evidence_level": "empty_template", "row_count": 0,
                      "protocol_sha256": manifest["protocol_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
