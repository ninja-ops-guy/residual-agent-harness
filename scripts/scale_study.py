"""Compare context overhead at several evidence sizes using scripted providers."""
import json
from pathlib import Path

from residual.config import load_config
from residual.evaluation import benchmark


def main():
    rows = []
    for noise in (4, 32, 256, 1024):
        report = benchmark(load_config(), cases=8, noise_lines=noise, modes=["cascade", "residual_fixed", "residual"])
        by_mode = {r["mode"]: r for r in report["summary"]}
        baseline, residual, fixed = by_mode["cascade"], by_mode["residual"], by_mode["residual_fixed"]
        rows.append({"noise_lines": noise, "cascade_bytes": baseline["remote_request_bytes"],
                     "residual_bytes": residual["remote_request_bytes"], "fixed_window_bytes": fixed["remote_request_bytes"],
                     "cascade_successes": baseline["successful"], "residual_successes": residual["successful"],
                     "request_byte_reduction_pct": 100 * (1 - residual["remote_request_bytes"] / baseline["remote_request_bytes"])})
    destination = Path(__file__).resolve().parents[1] / "docs"
    (destination / "scale-study.json").write_text(json.dumps({"simulation": True, "rows": rows}, indent=2) + "\n")
    lines = ["# Context size crossover", "", "Scripted controller simulation; framed request bytes, not measured LLM tokens or cost.", "",
             "| Background lines | Cascade bytes | Fixed-window bytes | Adaptive residual bytes | Reduction vs cascade | Passed, cascade / adaptive |",
             "| ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in rows:
        lines.append(f"| {r['noise_lines']} | {r['cascade_bytes']:,} | {r['fixed_window_bytes']:,} | {r['residual_bytes']:,} | "
                     f"{r['request_byte_reduction_pct']:.1f}% | {r['cascade_successes']}/8; {r['residual_successes']}/8 |")
    lines += ["", "The fixed-window policy loses to the cascade on tiny inputs. Adaptive residual sends the small relevant artifact in one capsule.",
              "All other limits and checks are unchanged; each mode starts without a cache.", ""]
    (destination / "scale-study.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
