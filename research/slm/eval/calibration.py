#!/usr/bin/env python3
"""Confidence calibration tooling for EXP-M6-SLM evaluation.

Stdlib-only. Implements the calibration metrics frozen in
EVALUATION-PROTOCOL.md (eval-protocol-v1.0.0) section 4:

  - Expected Calibration Error (ECE), 10 equal-width buckets by default
  - Brier score
  - Reliability diagram data (per-bucket confidence vs accuracy) with a
    matplotlib-free rendering (ASCII table or standalone SVG)
  - Threshold sweeps for escalation decisions (sweep an escalation
    confidence threshold and report FNER / UER per threshold, using the
    frozen metric names from the evaluation protocol)

Boundary statement: this module computes statistics over supplied
(verified) observations only. It does not access holdout labels, does
not inspect model weights, and does not train anything.

CLI:
  python calibration.py --help
  python calibration.py ece --input observations.jsonl
  python calibration.py brier --input observations.jsonl
  python calibration.py reliability --input observations.jsonl [--svg out.svg]
  python calibration.py sweep --input observations.jsonl [--steps 20]

Input format: JSON Lines, one record per decision:
  {"confidence": 0.83, "correct": true}
For sweep mode, records additionally carry escalation labels:
  {"confidence": 0.83, "correct": true,
   "escalation_required": true, "escalated": false}
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Sequence

DEFAULT_BUCKETS = 10  # frozen: ECE uses 10 equal-width buckets


@dataclass(frozen=True)
class CalibrationRecord:
    """One decision with a confidence score and a verified outcome."""

    confidence: float
    correct: bool
    escalation_required: Optional[bool] = None
    escalated: Optional[bool] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be in [0, 1], got %r" % self.confidence
            )


@dataclass(frozen=True)
class Bucket:
    """One equal-width confidence bucket of a reliability diagram."""

    lower: float
    upper: float
    count: int
    mean_confidence: float
    accuracy: float


@dataclass(frozen=True)
class SweepPoint:
    """Escalation-threshold sweep point using frozen metric names."""

    threshold: float
    fner: float  # false non-escalation rate
    uer: float  # unnecessary escalation rate
    escalated_fraction: float
    decisions: int


def load_records(path: str) -> List[CalibrationRecord]:
    """Load JSONL calibration records from ``path`` ('-' for stdin)."""
    stream = sys.stdin if path == "-" else open(path, "r", encoding="utf-8")
    records: List[CalibrationRecord] = []
    with stream:
        for lineno, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                records.append(
                    CalibrationRecord(
                        confidence=float(obj["confidence"]),
                        correct=bool(obj["correct"]),
                        escalation_required=obj.get("escalation_required"),
                        escalated=obj.get("escalated"),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                raise ValueError(
                    "%s:%d: invalid calibration record: %s" % (path, lineno, exc)
                ) from exc
    return records


def assign_buckets(
    records: Sequence[CalibrationRecord], n_buckets: int = DEFAULT_BUCKETS
) -> List[Bucket]:
    """Bin records into ``n_buckets`` equal-width confidence buckets."""
    if n_buckets < 1:
        raise ValueError("n_buckets must be >= 1")
    width = 1.0 / n_buckets
    groups: List[List[CalibrationRecord]] = [[] for _ in range(n_buckets)]
    for rec in records:
        idx = min(int(rec.confidence / width), n_buckets - 1)
        groups[idx].append(rec)
    buckets = []
    for i, group in enumerate(groups):
        if group:
            mean_conf = sum(r.confidence for r in group) / len(group)
            acc = sum(1.0 if r.correct else 0.0 for r in group) / len(group)
        else:
            mean_conf = 0.0
            acc = 0.0
        buckets.append(
            Bucket(
                lower=i * width,
                upper=(i + 1) * width,
                count=len(group),
                mean_confidence=mean_conf,
                accuracy=acc,
            )
        )
    return buckets


def expected_calibration_error(
    records: Sequence[CalibrationRecord], n_buckets: int = DEFAULT_BUCKETS
) -> float:
    """ECE: weighted mean |accuracy - confidence| over buckets."""
    if not records:
        raise ValueError("ECE requires at least one record")
    buckets = assign_buckets(records, n_buckets)
    total = len(records)
    return sum(
        (b.count / total) * abs(b.accuracy - b.mean_confidence)
        for b in buckets
        if b.count
    )


def brier_score(records: Sequence[CalibrationRecord]) -> float:
    """Brier score: mean squared error of confidence vs outcome."""
    if not records:
        raise ValueError("Brier score requires at least one record")
    return sum(
        (r.confidence - (1.0 if r.correct else 0.0)) ** 2 for r in records
    ) / len(records)


def reliability_table(
    records: Sequence[CalibrationRecord], n_buckets: int = DEFAULT_BUCKETS
) -> str:
    """Render a reliability diagram as an ASCII table (no matplotlib)."""
    buckets = assign_buckets(records, n_buckets)
    lines = [
        "bucket       count  mean_conf  accuracy  gap",
        "-----------  -----  ---------  --------  -----",
    ]
    for b in buckets:
        gap = b.accuracy - b.mean_confidence if b.count else 0.0
        lines.append(
            "[%.1f, %.1f)%s %5d  %9.4f  %8.4f  %+.4f"
            % (
                b.lower,
                b.upper,
                " " if b.upper < 1.0 else "]",
                b.count,
                b.mean_confidence,
                b.accuracy,
                gap,
            )
        )
    return "\n".join(lines)


def reliability_svg(
    records: Sequence[CalibrationRecord],
    n_buckets: int = DEFAULT_BUCKETS,
    width: int = 480,
    height: int = 480,
) -> str:
    """Render a reliability diagram as a standalone SVG (stdlib-only)."""
    buckets = assign_buckets(records, n_buckets)
    pad = 50
    plot_w = width - 2 * pad
    plot_h = height - 2 * pad

    def sx(x: float) -> float:
        return pad + x * plot_w

    def sy(y: float) -> float:
        return height - pad - y * plot_h

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
        % (width, height),
        '<rect width="100%" height="100%" fill="white"/>',
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="black"/>'
        % (pad, height - pad, width - pad, height - pad),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="black"/>'
        % (pad, pad, pad, height - pad),
        # perfect-calibration diagonal
        '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
        'stroke="gray" stroke-dasharray="4 4"/>'
        % (sx(0), sy(0), sx(1), sy(1)),
        '<text x="%d" y="%d" font-size="12" text-anchor="middle">'
        "mean confidence</text>" % (width // 2, height - 10),
        '<text x="14" y="%d" font-size="12" text-anchor="middle" '
        'transform="rotate(-90 14 %d)">accuracy</text>'
        % (height // 2, height // 2),
    ]
    for b in buckets:
        if not b.count:
            continue
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
            'fill="steelblue" fill-opacity="0.6"/>'
            % (
                sx(b.lower) + 1,
                sy(b.accuracy),
                plot_w / n_buckets - 2,
                max(plot_h * b.accuracy, 1.0),
            )
        )
        parts.append(
            '<circle cx="%.1f" cy="%.1f" r="3" fill="darkred"/>'
            % (sx(b.mean_confidence), sy(b.accuracy))
        )
    parts.append("</svg>")
    return "\n".join(parts)


def threshold_sweep(
    records: Sequence[CalibrationRecord], steps: int = 20
) -> List[SweepPoint]:
    """Sweep an escalation-confidence threshold.

    Decision rule under test: escalate when ``confidence < threshold``.
    Reports FNER (false non-escalation rate) and UER (unnecessary
    escalation rate) at each threshold, per the frozen definitions in
    EVALUATION-PROTOCOL.md sections 3-4. This is a decision-analysis
    aid only; the frozen FNER cap (0.02) is enforced by the evaluation
    pipeline, not here.
    """
    if steps < 2:
        raise ValueError("steps must be >= 2")
    labeled = [
        r
        for r in records
        if r.escalation_required is not None
    ]
    if not labeled:
        raise ValueError(
            "threshold sweep requires records with escalation_required"
        )
    points = []
    for i in range(steps + 1):
        thr = i / steps
        required = [r for r in labeled if r.escalation_required]
        taken = [r for r in labeled if r.confidence < thr]
        fne = sum(1 for r in required if r.confidence >= thr)
        ue = sum(1 for r in taken if not r.escalation_required)
        points.append(
            SweepPoint(
                threshold=thr,
                fner=fne / len(required) if required else 0.0,
                uer=ue / len(taken) if taken else 0.0,
                escalated_fraction=len(taken) / len(labeled),
                decisions=len(labeled),
            )
        )
    return points


def _dump(obj) -> str:
    if hasattr(obj, "__dataclass_fields__"):
        return json.dumps(asdict(obj), indent=2, sort_keys=True)
    return json.dumps(obj, indent=2, sort_keys=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", default="-", help="JSONL input path ('-' for stdin)"
    )
    parser.add_argument(
        "--buckets",
        type=int,
        default=DEFAULT_BUCKETS,
        help="number of equal-width buckets (frozen default: 10)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ece", help="print expected calibration error")
    sub.add_parser("brier", help="print Brier score")
    rel = sub.add_parser(
        "reliability", help="print reliability diagram (ASCII table)"
    )
    rel.add_argument("--svg", help="also write a standalone SVG here")
    sweep = sub.add_parser(
        "sweep", help="escalation threshold sweep (FNER/UER)"
    )
    sweep.add_argument(
        "--steps", type=int, default=20, help="number of sweep steps"
    )
    args = parser.parse_args(argv)

    records = load_records(args.input)
    if args.command == "ece":
        print("%.6f" % expected_calibration_error(records, args.buckets))
    elif args.command == "brier":
        print("%.6f" % brier_score(records))
    elif args.command == "reliability":
        print(reliability_table(records, args.buckets))
        if args.svg:
            with open(args.svg, "w", encoding="utf-8") as fh:
                fh.write(reliability_svg(records, args.buckets))
    elif args.command == "sweep":
        print(_dump([asdict(p) for p in threshold_sweep(records, args.steps)]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
