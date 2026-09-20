"""Optional GPU power sampling for SLM telemetry (vsms_per_watt input).

Resolution order: pynvml (NVML) -> nvidia-smi subprocess -> unmeasurable.
Every failure degrades gracefully: ``sample_watts()`` returns ``None`` and
the reason is exposed via ``degradation_reason`` so the caller can log it.
Energy is NEVER estimated silently (eval-protocol-v1.0.0 §6).
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional


class NvmlPowerSampler:
    """pynvml-based sampler; unavailable when pynvml or a GPU is absent."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.degradation_reason: Optional[str] = None
        self._nvml = None
        self._handle = None
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
            self._nvml = pynvml
        except Exception as exc:
            self.degradation_reason = f"pynvml_unavailable: {exc!r}"

    def sample_watts(self) -> Optional[float]:
        if self._nvml is None or self._handle is None:
            return None
        try:
            mw = self._nvml.nvmlDeviceGetPowerUsage(self._handle)
            return mw / 1000.0
        except Exception as exc:
            self.degradation_reason = f"nvml_sample_failed: {exc!r}"
            return None


class NvidiaSmiPowerSampler:
    """nvidia-smi subprocess fallback. Never raises."""

    def __init__(self, timeout_s: float = 2.0):
        self.timeout_s = timeout_s
        self.degradation_reason: Optional[str] = None
        if shutil.which("nvidia-smi") is None:
            self.degradation_reason = "nvidia_smi_not_found"

    def sample_watts(self) -> Optional[float]:
        if self.degradation_reason is not None:
            return None
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=power.draw",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=self.timeout_s, check=True)
            return float(out.stdout.strip().splitlines()[0])
        except Exception as exc:
            self.degradation_reason = f"nvidia_smi_failed: {exc!r}"
            return None


def default_power_sampler():
    """Best available sampler, or a NoneSampler (energy 'not measurable')."""
    nvml = NvmlPowerSampler()
    if nvml.degradation_reason is None:
        return nvml
    smi = NvidiaSmiPowerSampler()
    if smi.degradation_reason is None:
        return smi
    return NoneSampler(reason=f"{nvml.degradation_reason}; {smi.degradation_reason}")


class NoneSampler:
    def __init__(self, reason: str = "no_measurement_path"):
        self.degradation_reason = reason

    def sample_watts(self) -> Optional[float]:
        return None
