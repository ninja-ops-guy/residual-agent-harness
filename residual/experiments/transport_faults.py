"""Deterministic mesh delivery-fault experiments.

This module does not pretend to be a network stack. It feeds real signed MeshMessage
objects through MeshNode.receive_message under controlled duplicate, reorder, gap and
partition schedules, then measures verified catch-up through sync_history().

The goal is to measure protocol behavior when transport semantics are worse than the
in-process synchronous MeshSession happy path.
"""
from __future__ import annotations

import hashlib
import hmac
import statistics
import time
from typing import Any

from residual.core import digest
from residual.mesh import MeshIdentity, MeshMessageKind, MeshNode


SCENARIOS = ("clean", "duplicate", "reverse", "gap", "partition")


def _pair():
    keys = {
        "pk-a": hashlib.sha256(b"transport-a").digest(),
        "pk-b": hashlib.sha256(b"transport-b").digest(),
    }

    def verify(public_key, data, signature):
        key = keys.get(public_key)
        return bool(key) and hmac.compare_digest(
            hmac.new(key, data, hashlib.sha256).hexdigest(), signature
        )

    now = time.time_ns()
    a_key, b_key = keys["pk-a"], keys["pk-b"]
    a = MeshNode(
        MeshIdentity("dev-a", "A", "pk-a", ("chat",), "sim://a", now),
        lambda data: hmac.new(a_key, data, hashlib.sha256).hexdigest(),
        verify,
    )
    b = MeshNode(
        MeshIdentity("dev-b", "B", "pk-b", ("chat",), "sim://b", now),
        lambda data: hmac.new(b_key, data, hashlib.sha256).hexdigest(),
        verify,
    )
    a.connect_peer(b.identity)
    b.connect_peer(a.identity)
    return a, b


def _schedule(messages, scenario: str):
    if scenario == "clean":
        return list(messages)
    if scenario == "duplicate":
        return [message for original in messages for message in (original, original)]
    if scenario == "reverse":
        return list(reversed(messages))
    if scenario == "gap":
        return [message for index, message in enumerate(messages) if index % 2 == 0]
    if scenario == "partition":
        return []
    raise ValueError(f"unknown mesh delivery scenario: {scenario}")


def _trial(*, messages: int, scenario: str) -> dict[str, Any]:
    a, b = _pair()
    authored = [
        a.send_message(MeshMessageKind.CHAT, content=f"transport-{index}")
        for index in range(messages)
    ]
    schedule = _schedule(authored, scenario)

    accepted = 0
    rejected = 0
    delivery_started = time.perf_counter_ns()
    for message in schedule:
        if b.receive_message(message):
            accepted += 1
        else:
            rejected += 1
    delivery_finished = time.perf_counter_ns()

    pre_sync_count = len(b.chat.messages)
    pre_sync_head = b.chat.head_hash
    catchup_started = time.perf_counter_ns()
    appended = b.sync_history(a.chat.messages)
    catchup_finished = time.perf_counter_ns()
    replay_appended = b.sync_history(a.chat.messages)

    if not a.chat.verify() or not b.chat.verify():
        raise RuntimeError("mesh delivery experiment ended with invalid chat chain")
    if a.chat.head_hash != b.chat.head_hash:
        raise RuntimeError("mesh delivery experiment did not converge after verified catch-up")
    if replay_appended != 0:
        raise RuntimeError("verified history replay was not idempotent")

    delivery_ms = (delivery_finished - delivery_started) / 1_000_000.0
    catchup_ms = (catchup_finished - catchup_started) / 1_000_000.0
    return {
        "scenario": scenario,
        "messages": messages,
        "scheduled_deliveries": len(schedule),
        "pre_sync_accepted": accepted,
        "pre_sync_rejected": rejected,
        "pre_sync_message_count": pre_sync_count,
        "pre_sync_head": pre_sync_head,
        "sync_appended": appended,
        "delivery_ms": delivery_ms,
        "verified_catchup_ms": catchup_ms,
        "catchup_messages_s": (
            appended / (catchup_ms / 1000.0)
            if appended and catchup_ms > 0 else None
        ),
        "final_head": b.chat.head_hash,
        "converged": True,
        "replay_idempotent": True,
    }


def run_mesh_transport_fault_benchmark(
    *,
    messages: int = 100,
    scenarios: tuple[str, ...] = SCENARIOS,
    repeats: int = 3,
) -> dict[str, Any]:
    if not 1 <= messages <= 10000 or repeats < 1:
        raise ValueError("invalid transport-fault benchmark bounds")
    if not scenarios or len(scenarios) != len(set(scenarios)):
        raise ValueError("scenarios must be unique and nonempty")
    if any(scenario not in SCENARIOS for scenario in scenarios):
        raise ValueError("unsupported transport-fault scenario")

    runs = []
    for scenario in scenarios:
        for repeat in range(repeats):
            row = _trial(messages=messages, scenario=scenario)
            row["repeat"] = repeat
            runs.append(row)

    summary = []
    for scenario in scenarios:
        group = [row for row in runs if row["scenario"] == scenario]
        summary.append({
            "scenario": scenario,
            "pre_sync_accepted_median": statistics.median(
                row["pre_sync_accepted"] for row in group
            ),
            "pre_sync_rejected_median": statistics.median(
                row["pre_sync_rejected"] for row in group
            ),
            "sync_appended_median": statistics.median(
                row["sync_appended"] for row in group
            ),
            "delivery_median_ms": statistics.median(
                row["delivery_ms"] for row in group
            ),
            "verified_catchup_median_ms": statistics.median(
                row["verified_catchup_ms"] for row in group
            ),
            "all_converged": all(row["converged"] for row in group),
            "all_replays_idempotent": all(
                row["replay_idempotent"] for row in group
            ),
        })

    config = {
        "messages": messages,
        "scenarios": list(scenarios),
        "repeats": repeats,
    }
    return {
        "schema_version": "residual.mesh-transport-fault-experiment.v1",
        "kind": "mesh-delivery-faults",
        "evidence_level": "development_fixture",
        "simulation": True,
        "configuration": config,
        "runs": runs,
        "summary": summary,
        "claim_boundary": (
            "Uses real signed MeshMessage verification and real MeshNode chain/catch-up "
            "logic under deterministic delivery schedules. It does not emulate sockets, "
            "bandwidth, RTT, encryption, relay behavior, or consensus/finality."
        ),
        "benchmark_hash": digest(config),
    }
