from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
import hashlib
import json


def _freeze_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({
            str(key): _freeze_json_value(item)
            for key, item in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f'Acceptance values must be JSON-compatible, got {type(value).__name__}')


def _thaw_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: _thaw_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


@dataclass(frozen=True)
class ImprovementSpec:
    improvement_id: str
    observation: str
    hypothesis: str
    target_metrics: tuple[str, ...] = field(default_factory=tuple)
    preserve_metrics: tuple[str, ...] = field(default_factory=tuple)
    protected_invariants: tuple[str, ...] = field(default_factory=tuple)
    acceptance: Mapping[str, object] = field(default_factory=dict)
    human_approval_required: bool = True

    def __post_init__(self):
        if not self.improvement_id.strip():
            raise ValueError('Improvement ID cannot be blank or whitespace-only')
        if not self.observation.strip():
            raise ValueError('Observation cannot be blank or whitespace-only')
        if not self.hypothesis.strip():
            raise ValueError('Hypothesis cannot be blank or whitespace-only')
        if not self.target_metrics:
            raise ValueError('Target metrics cannot be empty')
        if not self.preserve_metrics:
            raise ValueError('Preserve metrics cannot be empty')
        if not self.protected_invariants:
            raise ValueError('Protected invariants cannot be empty')
        if any(not m.strip() for m in self.target_metrics):
            raise ValueError('Target metrics cannot contain blank or whitespace-only values')
        if any(not m.strip() for m in self.preserve_metrics):
            raise ValueError('Preserve metrics cannot contain blank or whitespace-only values')
        if any(not m.strip() for m in self.protected_invariants):
            raise ValueError('Protected invariants cannot contain blank or whitespace-only values')
        if not self.acceptance:
            raise ValueError('Acceptance cannot be empty')
        if not self.human_approval_required:
            raise ValueError('Human approval required cannot be False')

        object.__setattr__(self, 'acceptance', _freeze_json_value(self.acceptance))

    def to_dict(self) -> dict:
        return {
            'improvement_id': self.improvement_id,
            'observation': self.observation,
            'hypothesis': self.hypothesis,
            'target_metrics': list(self.target_metrics),
            'preserve_metrics': list(self.preserve_metrics),
            'protected_invariants': list(self.protected_invariants),
            'acceptance': _thaw_json_value(self.acceptance),
            'human_approval_required': self.human_approval_required,
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'), ensure_ascii=False)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode('utf-8')).hexdigest()
