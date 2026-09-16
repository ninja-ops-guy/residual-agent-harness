"""Synthetic NetOps/SecOps task templates for the soak harness (N9-R9).

Tasks are deterministic functions of (seed, day, index) so a resumed
soak regenerates the identical task stream.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

NETOPS_TEMPLATES: Tuple[str, ...] = (
    "rotate interface description on {device}",
    "reconcile BGP neighbor state for {device}",
    "audit ACL entries on {device}",
    "drain and upgrade firmware on {device}",
    "verify OSPF adjacency stability on {device}",
    "collect interface counters from {device}",
)

SECOPS_TEMPLATES: Tuple[str, ...] = (
    "triage EDR alert {alert_id} on {host}",
    "hunt for lateral movement from {host}",
    "isolate host {host} pending forensic capture",
    "review failed auth burst against {host}",
    "rotate exposed credential reported by {host}",
    "validate firewall rule change ticket {alert_id}",
)

_DEVICES = ("core-rtr-01", "edge-sw-14", "dist-sw-07", "fw-perim-02", "br-rtr-33")
_HOSTS = ("ws-1042", "srv-db-03", "vpn-gw-01", "ws-2210", "print-05")


@dataclass(frozen=True)
class SyntheticTask:
    task_id: str
    domain: str  # "netops" | "secops"
    prompt: str
    difficulty: str
    expected_tokens: int
    unsafe: bool = False  # True when the task carries adversarial content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "prompt": self.prompt,
            "difficulty": self.difficulty,
            "expected_tokens": self.expected_tokens,
            "unsafe": self.unsafe,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyntheticTask":
        return cls(
            task_id=data["task_id"], domain=data["domain"], prompt=data["prompt"],
            difficulty=data["difficulty"], expected_tokens=data["expected_tokens"],
            unsafe=data.get("unsafe", False),
        )


def make_task(seed: int, day: int, index: int) -> SyntheticTask:
    """Deterministically generate the ``index``-th task of ``day``."""
    rng = random.Random(f"{seed}:task:{day}:{index}")
    domain = "netops" if rng.random() < 0.5 else "secops"
    if domain == "netops":
        template = rng.choice(NETOPS_TEMPLATES)
        prompt = template.format(device=rng.choice(_DEVICES))
    else:
        template = rng.choice(SECOPS_TEMPLATES)
        prompt = template.format(host=rng.choice(_HOSTS), alert_id=f"A-{rng.randint(10000, 99999)}")
    difficulty = rng.choices(["low", "medium", "high"], weights=[50, 35, 15])[0]
    base = {"low": 2000, "medium": 4000, "high": 8000}[difficulty]
    return SyntheticTask(
        task_id=f"soak-d{day:03d}-{index:05d}",
        domain=domain,
        prompt=prompt,
        difficulty=difficulty,
        expected_tokens=int(base * rng.uniform(0.8, 1.2)),
    )
