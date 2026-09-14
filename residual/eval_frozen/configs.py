"""EVAL-R2/R3: configurations R0-R5 with held-constant experimental factors.

Every configuration pins the same model/provider/version, prompting policy,
inference settings, task corpus, tool environment, and grader. Only the
control-layer stack varies across ablations. Any deviation must be declared
explicitly in ``varied_factors``.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core import ContractError, canonical, digest, identifier

#: Factors held constant across all R0-R5 ablations (EVAL-R3). The fixture
#: pins a scripted deterministic engine; live runs must relabel these fields
#: and set evidence_level="live_model".
CONTROLLED_CONSTANTS: dict[str, object] = {
    "model": {
        "provider": "scripted-fixture",
        "model_id": "deterministic-engine-v1",
        "model_version": "1.0.0",
    },
    "prompting_policy": {
        "policy_id": "fixed-zero-shot-v1",
        "system_prompt_sha256": digest("residual-eval001-system-prompt-v1"),
    },
    "inference_settings": {
        "temperature": 0.0,
        "top_p": 1.0,
        "max_output_tokens": 512,
        "seeded": True,
    },
    "tool_environment": {
        "environment_id": "scripted-sandbox-v1",
        "tools": ("calculator", "string-tool"),
    },
    "grader": {
        "grader_id": "exact-match-grader-v1",
        "grader_version": "1.0.0",
    },
}


@dataclass(frozen=True)
class ExperimentConfig:
    """One ablation configuration (R0-R5).

    ``control_layers`` names the mechanisms stacked on top of the raw worker;
    every other experimental factor is inherited from CONTROLLED_CONSTANTS.
    """

    config_id: str
    label: str
    control_layers: tuple[str, ...]
    constants: dict[str, object]
    varied_factors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        identifier(self.config_id)
        if not self.label:
            raise ContractError("config label required")
        for layer in self.control_layers:
            identifier(layer)
        for factor in self.varied_factors:
            if factor in self.constants:
                raise ContractError("varied factor must not also be held constant")

    @property
    def sha256(self) -> str:
        return digest({
            "config_id": self.config_id,
            "control_layers": list(self.control_layers),
            "constants": self.constants,
            "varied_factors": list(self.varied_factors),
        })


def _config(config_id: str, label: str, layers: tuple[str, ...]) -> ExperimentConfig:
    return ExperimentConfig(config_id=config_id, label=label,
                            control_layers=layers, constants=CONTROLLED_CONSTANTS)


#: R0-R5 ablation ladder (EVAL-R2). Layers are cumulative.
CONFIGURATIONS: tuple[ExperimentConfig, ...] = (
    _config("R0", "raw unconstrained execution", ()),
    _config("R1", "orchestrated decomposition", ("orchestration",)),
    _config("R2", "contracted worker interface", ("orchestration", "contracts")),
    _config("R3", "constrained + observed + verified",
            ("orchestration", "contracts", "constraints", "observation", "verification")),
    _config("R4", "COVD: R3 + deterministic integration",
            ("orchestration", "contracts", "constraints", "observation", "verification",
             "deterministic_integration")),
    _config("R5", "dynamic swarm orchestration",
            ("orchestration", "contracts", "constraints", "observation", "verification",
             "deterministic_integration", "dynamic_swarm")),
)

CONFIG_IDS: tuple[str, ...] = tuple(config.config_id for config in CONFIGURATIONS)


def get_config(config_id: str) -> ExperimentConfig:
    for config in CONFIGURATIONS:
        if config.config_id == config_id:
            return config
    raise ContractError(f"unknown configuration {config_id}")


def constants_agree(configs: tuple[ExperimentConfig, ...] = CONFIGURATIONS) -> bool:
    """EVAL-R3 check: every configuration must hold the same constants."""
    reference = canonical(configs[0].constants)
    return all(canonical(config.constants) == reference for config in configs)
