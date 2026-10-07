"""Deterministic fixture observations for OBS-R8 / Gate C.

The fixture is fully deterministic: fixed schema, fixed values, no clocks,
no randomness. Identical calls produce byte-identical observation sets,
which produce byte-identical report hashes.
"""
from __future__ import annotations

from .schema import ALL_PHASES, OBSERVATION_SCHEMA_VERSION

FIXTURE_ID = "obs006-fixture-v1"


def _obs(kind, **fields):
    out = {"kind": kind, "schema_version": OBSERVATION_SCHEMA_VERSION}
    out.update(fields)
    return out


def build_fixture_observations() -> list:
    """Build the deterministic raw observation set covering every family."""
    obs = []
    # execution (3 tasks across 2 classes; 2 pass, 1 fail; correctness labels)
    obs += [
        _obs("execution", task_class="code", outcome="pass",
             worker_seconds=1.25, correct=True, tokens_input=400, tokens_output=120),
        _obs("execution", task_class="code", outcome="pass",
             worker_seconds=2.50, correct=True, tokens_input=410, tokens_output=90),
        _obs("execution", task_class="analysis", outcome="fail",
             worker_seconds=0.75, correct=False),  # missing optional token fields
    ]
    # acceptance (2 accepted; one is correct, one is a false accept)
    obs += [
        _obs("acceptance", task_class="code", correct=True),
        _obs("acceptance", task_class="code", correct=False),
    ]
    # rejection (1 rejected for verification)
    obs.append(_obs("rejection", task_class="analysis", reason="verification"))
    # verification (2 pass, 1 fail)
    obs += [
        _obs("verification", task_class="code", verdict="pass",
             verification_seconds=0.20, verifier_identity="verifier-a"),
        _obs("verification", task_class="code", verdict="pass",
             verification_seconds=0.30),  # missing optional verifier_identity
        _obs("verification", task_class="analysis", verdict="fail",
             verification_seconds=0.10, verifier_identity="verifier-a"),
    ]
    # integration (1 integrated, 1 conflicted)
    obs += [
        _obs("integration", result="integrated", integration_seconds=0.05,
             strategy="fast_forward"),
        _obs("integration", result="conflicted", integration_seconds=0.08),
    ]
    # conflicts
    obs.append(_obs("conflict", conflict_kind="write_write", resolution="retry"))
    # retries
    obs.append(_obs("retry", task_class="analysis", attempt=2, cause="conflict"))
    # resource consumption
    obs += [
        _obs("resource", resource="tokens_input", amount=810),
        _obs("resource", resource="tokens_output", amount=210),
        _obs("resource", resource="cpu_seconds", amount=3.5),
    ]
    # orchestration timing: one sample per phase (OBS-R5)
    phase_seconds = {
        "planning": 0.10, "dispatch": 0.02, "context_packaging": 0.15,
        "worker_runtime": 4.50, "verification": 0.60, "integration": 0.13,
    }
    for phase in ALL_PHASES:
        obs.append(_obs("orchestration_timing", phase=phase,
                        seconds=phase_seconds[phase]))
    return obs
