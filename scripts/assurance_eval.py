from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.assurance import (
    AdaptiveEvaluation,
    AssuranceClass,
    FrozenAssuranceCase,
    FrozenAssuranceWorkload,
    MarketProfile,
    VerifierDefect,
    evaluate_verifier_campaign,
)


def workload() -> FrozenAssuranceWorkload:
    return FrozenAssuranceWorkload(
        name="path-to-10-mixed-granularity-v1",
        seed=42,
        cases=(
            FrozenAssuranceCase("small-code-1", "small-edit", "code", AssuranceClass.ROUTINE, .90,
                True, True, .01, .20, 50, 450, "economy@1", {"economy@1": True, "strong@1": True}),
            FrozenAssuranceCase("small-code-2", "small-edit", "code", AssuranceClass.ROUTINE, .90,
                True, True, .01, .18, 45, 410, "economy@1", {"economy@1": True, "strong@1": True}),
            FrozenAssuranceCase("batch-code-1", "batch", "code", AssuranceClass.IMPORTANT, .95,
                False, True, .04, .16, 120, 260, "strong@1", {"economy@1": False, "strong@1": True}),
            FrozenAssuranceCase("batch-code-2", "batch", "code", AssuranceClass.IMPORTANT, .95,
                False, True, .05, .17, 150, 280, "strong@1", {"economy@1": False, "strong@1": True}),
            FrozenAssuranceCase("security-code-1", "security", "code", AssuranceClass.SECURITY_CRITICAL, .98,
                True, True, .08, .24, 180, 340, "strong@1", {"economy@1": False, "strong@1": True}),
            FrozenAssuranceCase("security-code-2", "security", "code", AssuranceClass.SECURITY_CRITICAL, .98,
                True, True, .09, .25, 190, 350, "strong@1", {"economy@1": False, "strong@1": True}),
        ),
    )


def engines() -> tuple[MarketProfile, ...]:
    return (
        MarketProfile("economy@1", frozenset({"code"}), .01, 50, alpha=30, beta=3, trials=31),
        MarketProfile("strong@1", frozenset({"code"}), .06, 90, alpha=200, beta=1, trials=199),
    )


def verifier_campaign():
    defects = []
    for i in range(24):
        acceptable = i % 3 != 0
        passed = acceptable
        defects.append(VerifierDefect(f"known-{i:02d}", acceptable, passed, .98))
    # Two intentionally missed defects make recall/FAR measurable instead of perfect by construction.
    defects[0] = VerifierDefect("known-00", False, True, .99)
    defects[9] = VerifierDefect("known-09", False, True, .99)
    return evaluate_verifier_campaign("host:frozen-security-verifier", defects)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run frozen adaptive-assurance evaluation")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    frozen = workload()
    report = AdaptiveEvaluation(frozen, engines()).run()
    campaign = verifier_campaign()
    payload = {
        "schema_version": "residual.assurance-evidence.v1",
        "workload_sha256": frozen.sha256,
        "adaptive_evaluation": report,
        "verifier_campaign": {
            "samples": campaign.samples,
            "false_accepts": campaign.false_accepts,
            "false_rejects": campaign.false_rejects,
            "defect_recall": campaign.defect_recall,
            "false_accept_rate": campaign.false_accept_rate,
            "posterior_mean": campaign.posterior_mean,
            "lower_credible_bound": campaign.lower_credible_bound,
            "requires_hitl": campaign.requires_hitl,
        },
        "claim_scope": "Deterministic synthetic fixture evidence only; does not establish production model superiority.",
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
