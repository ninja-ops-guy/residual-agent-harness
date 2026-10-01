"""Synthetic v2 decision example. Offline by default; never authorizes actions."""
from __future__ import annotations

import argparse
import json
import os
import sys

from residual.decision_models import ClefAdapter, DecisionError, DecisionRequest, replay_clef


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("clef", "clef-flash"), default="clef-flash")
    parser.add_argument("--live", action="store_true", help="Make one billable Cloudflare request")
    parser.add_argument("--ack-external-egress", action="store_true",
                        help="Acknowledge sending this synthetic state to Cloudflare")
    args = parser.parse_args()
    request = DecisionRequest.build(
        subject="SYNTHETIC-INCIDENT-001",
        state={"synthetic": True, "event": "Checkout errors affect all test customers."},
        questions={
            "urgent": {"type": "noul", "instructions": "Does this incident need urgent review?"},
            "team": {"type": "choice", "criteria": {"network": "Network incident", "app": "Application incident"}},
            "severity": {"type": "score", "criteria": ["Low", "Medium", "High"]},
        },
        evidence_refs=("fixture:synthetic-incident-001",),
    )
    try:
        if args.live:
            if not args.ack_external_egress:
                raise DecisionError("EXPLICIT_EGRESS_ACK_REQUIRED")
            account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
            token = os.environ.get("CLOUDFLARE_AUTH_TOKEN", "")
            if not account or not token:
                raise DecisionError("CLOUDFLARE_CREDENTIALS_MISSING")
            evidence = ClefAdapter(account, token, model=args.model, enabled=True).evaluate(request)
        else:
            # Invented test probabilities, NOT captured provider inference.
            fixture = {"model": args.model, "answers": {
                "urgent": {"type": "noul", "noul": 0.95},
                "team": {"type": "choice", "choice": "app", "confidence": 0.6,
                         "probabilities": {"network": 0.1, "app": 0.9}},
                "severity": {"type": "score", "score": 1.7, "confidence": 0.7,
                             "legend": {"0": "Low", "1": "Medium", "2": "High"},
                             "probabilities": {"0": 0.1, "1": 0.1, "2": 0.8}},
            }}
            evidence = replay_clef(request, json.dumps(fixture).encode(), model=args.model)
        print(json.dumps(evidence.to_dict(), indent=2, sort_keys=True))
        return 0
    except DecisionError as exc:
        print(f"Decision adapter stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
