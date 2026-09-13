"""Synthetic incident workload and explicitly scripted workers, not real LLM results."""
from __future__ import annotations

import math
from dataclasses import replace

from .core import Artifact, Obligation, Registry, Task, Verdict, canonical, strict_json
from .providers import Provider, Reply, Usage


ACTIONS = {"dns": "Restore the approved DNS configuration and retest name resolution.",
           "certificate": "Renew the service certificate and retest TLS validation.",
           "firewall": "Restore the approved firewall rule and retest the connection.",
           "application": "Restart the failed application service and verify health."}
SIGNALS = {"dns": "PROBE: direct IP succeeds; hostname fails with NXDOMAIN; DNS configuration differs from baseline.",
           "certificate": "PROBE: TCP succeeds; TLS validation fails; certificate notAfter is before the test timestamp.",
           "firewall": "PROBE: route exists; SYN reaches the gateway; firewall audit explicitly records a DENY for this flow.",
           "application": "PROBE: DNS and TLS succeed; application health is failed; service process is stopped."}


def diagnosis(text):
    for cause, signal in SIGNALS.items():
        if signal in text:
            return cause
    raise ValueError("no sufficient probe evidence")


def register(registry: Registry):
    def count(ctx):
        return sum("level=ERROR" in line for line in ctx.evidence("telemetry").splitlines())

    def count_check(value, ctx):
        return Verdict.passed() if type(value) is int and value == count(ctx) else Verdict.fail(
            "count_mismatch", "Count exactly the ERROR-level records in telemetry.")

    def cause_check(value, ctx):
        expected = diagnosis(ctx.evidence("probe"))
        return Verdict.passed() if value == expected else Verdict.fail(
            "probe_contradiction", "The proposed cause conflicts with the diagnostic PROBE record; inspect it.")

    def action(ctx):
        return strict_json(ctx.evidence("actions"))[ctx.dependency("cause")]

    def action_check(value, ctx):
        return Verdict.passed() if value == action(ctx) else Verdict.fail(
            "action_inconsistent", "Select the policy action matching the accepted cause.")

    registry.check("incident_count", count_check, "1")
    registry.check("incident_cause", cause_check, "1")
    registry.check("incident_action", action_check, "1")
    registry.solver("incident_count", count)
    registry.solver("incident_action", action)


def make_case(index=0, noise_lines=256):
    cause = list(SIGNALS)[index % len(SIGNALS)]
    telemetry = "\n".join(f"event={i:05d} level={'ERROR' if i % (7 + index % 3) == 0 else 'INFO'} service=line-controller"
                           for i in range(noise_lines * 2)) + "\n"
    probe = "Diagnostic log. Final record contains the decisive connection probe.\n"
    probe += "\n".join(f"sample={i:05d} background sensor poll completed normally" for i in range(noise_lines)) + "\n"
    probe += SIGNALS[cause] + "\n"
    artifacts = {
        "telemetry": Artifact("telemetry", telemetry, True),
        "probe": Artifact("probe", probe, True),
        "actions": Artifact("actions", canonical(ACTIONS), True)}
    return Task(f"incident-{index}", "Count error records, diagnose the failed connection, and select the approved corrective action.",
                artifacts, (
                    Obligation("error_count", "Return an integer count of telemetry records containing level=ERROR.",
                               "incident_count", ("telemetry",), solver="incident_count"),
                    Obligation("cause", "Return one cause string: dns, certificate, firewall, or application. Use the diagnostic PROBE record.",
                               "incident_cause", ("probe",), ("error_count",)),
                    Obligation("action", "Return the exact policy action string for the accepted cause.",
                               "incident_action", ("actions",), ("cause",), solver="incident_action")))


class DemoProvider(Provider):
    """Controller fixture: local guesses application; expert reads visible evidence.

    This is deliberately deterministic and is NEVER an LLM accuracy benchmark.
    Values are computed only from the packet (no hidden fixture oracle access).
    """
    def __init__(self, role="local"):
        self.role = role
        self.name = "scripted-demo-" + role
        self.placement = "local" if role == "local" else "remote"

    def generate(self, packet, max_output_tokens):
        visible = {}
        for item in packet["evidence"]:
            visible.setdefault(item["artifact_id"], []).append(item)
        texts = {key: "".join(i["text"] for i in sorted(items, key=lambda x: x["start_line"]))
                 for key, items in visible.items()}
        manifest = {m["artifact_id"]: m for m in packet["manifest"]}
        updates, requests = {}, []
        for o in packet["obligations"]:
            if o["id"] == "cause" and self.role == "local":
                updates[o["id"]] = "application"
                continue
            try:
                if o["id"] == "cause":
                    updates[o["id"]] = diagnosis(texts.get("probe", ""))
                elif o["id"] == "error_count":
                    windows = visible.get("telemetry", [])
                    if not windows or sum(i["end_line"] - i["start_line"] + 1 for i in windows) < manifest["telemetry"]["line_count"]:
                        raise ValueError("telemetry is incomplete")
                    updates[o["id"]] = sum("level=ERROR" in line for line in texts["telemetry"].splitlines())
                elif o["id"] == "action":
                    cause = packet["accepted_dependencies"]["cause"]["value"]
                    updates[o["id"]] = strict_json(texts["actions"])[cause]
            except (ValueError, KeyError):
                artifact_id = o["evidence_ids"][0]
                end = manifest[artifact_id]["line_count"]
                requests.append({"obligation_id": o["id"], "artifact_id": artifact_id,
                                 "start_line": max(1, end - 3), "end_line": end})
        text = canonical({"updates": updates, "requests": requests})
        return Reply(text, Usage(math.ceil(self.wire_size(packet, max_output_tokens) / 4),
                                  math.ceil(len(text.encode()) / 4), 0, "simulation"), 0, "stop")
