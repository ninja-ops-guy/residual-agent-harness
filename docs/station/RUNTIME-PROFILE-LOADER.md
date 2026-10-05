# Runtime Profile Loader Contract

**Status:** Proposed / Backlog  
**Scope:** Station runtime profile loading, lifecycle, ownership, and profile isolation  
**Primary integration target:** Omarchy as the first desktop runtime profile  
**Related specs:** Runtime profile interfaces, capability discovery, desktop adapters, provider discovery, GPU discovery, doctor command, runtime qualification

This document defines the canonical profile loader contract for RESIDUAL runtime profiles. It is intentionally generic: Omarchy is the first proving profile, not a Station dependency.

---

## 1. Objective

Station SHALL load runtime profiles through a single canonical loader interface.

Runtime profiles SHALL expose platform capabilities, adapters, environment metadata, providers, GPU devices, and health through typed contracts.

Runtime profiles SHALL NOT modify Station mission semantics, verification semantics, approval semantics, receipt semantics, worker authority, or integration authority.

The loader SHALL make platform integration deterministic, inspectable, testable, and safely degradable.

---

## 2. Non-goals

This contract SHALL NOT:

- make Omarchy mandatory;
- add Omarchy-specific branches to Station core;
- allow profiles to approve missions;
- allow profiles to write receipts;
- allow profiles to redefine verifiers;
- allow profiles to mutate provider credentials;
- allow profiles to bypass human gates;
- allow profiles to change worker execution policy after Station startup;
- require a desktop environment for Station execution.

---

## 3. Ownership boundary summary

| Component | Owns | Does not own |
| --- | --- | --- |
| Station | mission authority, verifier authority, receipts, worker orchestration, policy, integration state | platform probing details, desktop-specific commands |
| Runtime profile loader | profile discovery, manifest validation, load ordering, lifecycle transitions, profile health aggregation | mission execution, approval decisions, verifier results |
| Runtime profile | host/environment detection, capability reporting, adapter registration, provider/GPU discovery | Station policy, receipts, protected state, credentials |
| Desktop adapter | notifications, clipboard operations, launcher entries, theme/presence metadata | mission authority, evidence authority, approval authority |
| Provider discovery | passive provider detection and availability metadata | model calls, paid inference, key creation, key mutation |
| Doctor/qualification | diagnostic reporting and conformance checks | runtime approval, mission acceptance, release claims beyond evidence |

---

## 4. Canonical loader interface

The profile loader SHALL be the only Station-facing mechanism for profile discovery and activation.

```python
class RuntimeProfileLoader:
    def discover_manifests(self) -> tuple[RuntimeProfileManifest, ...]: ...

    def select_profile(
        self,
        request: RuntimeProfileSelectionRequest,
    ) -> RuntimeProfileSelectionResult: ...

    def load(
        self,
        manifest: RuntimeProfileManifest,
    ) -> RuntimeProfileLoadResult: ...

    def initialize(
        self,
        loaded_profile: LoadedRuntimeProfile,
    ) -> RuntimeProfileInitializationResult: ...

    def activate(
        self,
        initialized_profile: InitializedRuntimeProfile,
    ) -> RuntimeProfileActivationResult: ...

    def health(self) -> RuntimeProfileLoaderHealth: ...

    def shutdown(self) -> RuntimeProfileShutdownResult: ...
```

Rules:

- `discover_manifests()` SHALL be side-effect free.
- `select_profile()` SHALL be deterministic for the same request and host state.
- `load()` SHALL validate contracts before importing profile implementation code.
- `initialize()` MAY perform bounded host probing.
- `activate()` SHALL only publish immutable capability/adaptor state to Station.
- `shutdown()` SHALL be best-effort and non-authoritative.

---

## 5. Loader selection request

```python
@dataclass(frozen=True)
class RuntimeProfileSelectionRequest:
    requested_profile_id: str | None
    allow_auto_detect: bool
    allow_desktop_profiles: bool
    allow_headless_profiles: bool
    required_capabilities: tuple[str, ...]
    preferred_capabilities: tuple[str, ...]
    disabled_profiles: tuple[str, ...]
    metadata: Mapping[str, Any]
```

Selection rules:

- Explicit `requested_profile_id` wins over auto-detection when valid.
- Disabled profiles SHALL never be selected.
- Missing required capabilities SHALL make a profile ineligible.
- Preferred capabilities MAY affect ordering but SHALL NOT override required constraints.
- If no profile qualifies, the loader SHALL return the generic fallback profile.

---

## 6. Loader selection result

```python
@dataclass(frozen=True)
class RuntimeProfileSelectionResult:
    selected_profile_id: str
    selected_manifest_path: str | None
    reason: str
    confidence: float
    candidates: tuple[RuntimeProfileCandidate, ...]
    issues: tuple[RuntimeIssue, ...]
```

```python
@dataclass(frozen=True)
class RuntimeProfileCandidate:
    profile_id: str
    manifest_path: str | None
    eligible: bool
    confidence: float
    reasons: tuple[str, ...]
    issues: tuple[RuntimeIssue, ...]
```

Rules:

- `confidence` SHALL be between `0.0` and `1.0`.
- Rejected candidates SHALL remain visible for diagnostics.
- The fallback profile SHALL appear as a candidate.

---

## 7. Runtime profile manifest contract

Every runtime profile SHALL ship a manifest.

```python
@dataclass(frozen=True)
class RuntimeProfileManifest:
    id: str
    name: str
    version: str
    contract_version: str
    platform: Platform
    profile_kind: RuntimeProfileKind
    entrypoint: str
    capabilities_declared: tuple[str, ...]
    adapters_declared: tuple[str, ...]
    dependencies: tuple[RuntimeProfileDependency, ...]
    detection: RuntimeProfileDetectionSpec
    permissions: RuntimeProfilePermissionSpec
    lifecycle: RuntimeProfileLifecycleSpec
    metadata: Mapping[str, Any]
```

```python
class RuntimeProfileKind(str, Enum):
    GENERIC = "generic"
    DESKTOP = "desktop"
    HEADLESS = "headless"
    CONTAINER = "container"
    REMOTE = "remote"
```

Manifest rules:

- `id` SHALL be globally stable.
- `entrypoint` SHALL point to a profile implementation, not Station core.
- `capabilities_declared` SHALL be declarative and non-authoritative until probed.
- `permissions` SHALL enumerate requested side effects before activation.
- `metadata` SHALL be JSON-serializable.

---

## 8. Dependency contract

```python
@dataclass(frozen=True)
class RuntimeProfileDependency:
    id: str
    kind: Literal["binary", "python_package", "system_service", "file", "environment"]
    required: bool
    version_constraint: str | None
    detection_hint: str | None
    remediation: str | None
```

Rules:

- Missing required dependencies SHALL make the profile degraded or ineligible depending on lifecycle phase.
- Missing optional dependencies SHALL produce warnings only.
- Dependencies SHALL NOT be installed by the loader unless a separate explicit installer command is invoked.

---

## 9. Detection contract

```python
@dataclass(frozen=True)
class RuntimeProfileDetectionSpec:
    markers: tuple[RuntimeProfileMarker, ...]
    minimum_confidence: float
    fallback_profile_id: str
```

```python
@dataclass(frozen=True)
class RuntimeProfileMarker:
    id: str
    kind: Literal["file", "command", "env", "process", "desktop", "package", "kernel", "custom_probe"]
    expected: str | None
    weight: float
    required: bool
```

Detection rules:

- Detection SHALL be bounded by timeout.
- Detection SHALL be read-only.
- Detection SHALL NOT mutate shell files, desktop entries, provider config, or credentials.
- A profile MAY run in partial/degraded mode when non-required markers are absent.

---

## 10. Permission contract

```python
@dataclass(frozen=True)
class RuntimeProfilePermissionSpec:
    may_send_notifications: bool
    may_write_clipboard: bool
    may_read_clipboard: bool
    may_register_launcher_entries: bool
    may_write_shell_config: bool
    may_start_desktop_service: bool
    may_probe_local_network: bool
    may_probe_provider_endpoints: bool
    may_read_environment_keys: bool
```

Permission rules:

- Read-only discovery SHALL be allowed by default.
- Mutating operations SHALL require explicit operator approval or installation mode.
- Clipboard reads SHALL be disabled by default.
- Provider endpoint probes SHALL be health checks only and SHALL NOT send prompts.
- Credential values SHALL never be serialized.

---

## 11. Lifecycle state machine

Runtime profiles SHALL move through this state machine:

```text
DISCOVERED
  -> SELECTED
  -> LOADED
  -> INITIALIZING
  -> INITIALIZED
  -> ACTIVATING
  -> ACTIVE
  -> DEGRADED
  -> SHUTTING_DOWN
  -> STOPPED
```

Failure states:

```text
LOAD_FAILED
INITIALIZATION_FAILED
ACTIVATION_FAILED
SHUTDOWN_FAILED
```

State transition rules:

- `DISCOVERED` means manifest observed, not trusted.
- `SELECTED` means chosen by policy, not imported.
- `LOADED` means manifest and entrypoint validated.
- `INITIALIZED` means probes completed and immutable capability set produced.
- `ACTIVE` means Station may consume profile contracts.
- `DEGRADED` means Station may continue with reduced profile services.
- Failure states SHALL produce structured RuntimeIssue records.

---

## 12. Lifecycle method ownership

| Phase | Loader action | Profile action | Station action |
| --- | --- | --- | --- |
| Discover | enumerate manifests | none | none |
| Select | rank candidates | none | supply request policy |
| Load | validate manifest, import entrypoint | expose implementation object | none |
| Initialize | call profile initialization | probe host, build immutable contracts | wait |
| Activate | register immutable profile result | no new probing unless allowed | consume contracts |
| Runtime | aggregate health | report health/adapters | execute missions independently |
| Shutdown | call teardown | cleanup best-effort adapters | continue protected shutdown |

---

## 13. Loaded profile contract

```python
@dataclass(frozen=True)
class LoadedRuntimeProfile:
    manifest: RuntimeProfileManifest
    profile: RuntimeProfile
    loaded_at: str
    loader_version: str
    issues: tuple[RuntimeIssue, ...]
```

Rules:

- A loaded profile is not active.
- Loading SHALL NOT publish capabilities to Station.
- Loading SHALL NOT perform mutating desktop integration.

---

## 14. Initialized profile contract

```python
@dataclass(frozen=True)
class InitializedRuntimeProfile:
    manifest: RuntimeProfileManifest
    environment: EnvironmentInfo
    capabilities: CapabilitySet
    adapters: AdapterRegistry
    providers: tuple[ProviderInfo, ...]
    gpu_devices: tuple[GPUDevice, ...]
    health: RuntimeHealth
    initialized_at: str
    issues: tuple[RuntimeIssue, ...]
```

Rules:

- Initialization SHALL produce immutable environment and capability snapshots.
- Providers and GPU devices SHALL be passive discovery outputs.
- Initialization SHALL NOT register launcher entries unless installer mode is explicitly active.

---

## 15. Activation result contract

```python
@dataclass(frozen=True)
class RuntimeProfileActivationResult:
    profile_id: str
    active: bool
    activated_at: str | None
    environment: EnvironmentInfo
    capabilities: CapabilitySet
    adapters: AdapterRegistry
    health: RuntimeHealth
    issues: tuple[RuntimeIssue, ...]
```

Activation rules:

- Activation SHALL publish contracts to Station.
- Activation SHALL NOT alter Station authority.
- Activation SHALL fail closed if contracts fail validation.
- Activation MAY produce `active=false` with fallback profile active.

---

## 16. Loader health contract

```python
@dataclass(frozen=True)
class RuntimeProfileLoaderHealth:
    state: RuntimeState
    checked_at: str
    active_profile_id: str | None
    loader_version: str
    known_profiles: tuple[str, ...]
    issues: tuple[RuntimeIssue, ...]
    metadata: Mapping[str, Any]
```

---

## 17. Shutdown contract

```python
@dataclass(frozen=True)
class RuntimeProfileShutdownResult:
    profile_id: str | None
    stopped: bool
    stopped_at: str | None
    issues: tuple[RuntimeIssue, ...]
```

Shutdown rules:

- Shutdown SHALL be best-effort.
- Profile shutdown failure SHALL NOT corrupt Station shutdown.
- Profiles SHALL NOT write final mission state.
- Profiles MAY unregister transient services they created during the same run.

---

## 18. Authority boundaries

Runtime profiles MAY:

- report capabilities;
- report environment metadata;
- report provider availability;
- report GPU availability;
- expose optional desktop adapters;
- produce diagnostic reports;
- emit runtime events;
- recommend remediation.

Runtime profiles SHALL NOT:

- accept worker output;
- reject worker output;
- approve missions;
- change verifier policy;
- write Station receipts;
- mutate protected branches;
- create or modify provider credentials;
- bypass HITL gates;
- change budget authority;
- change mission DAGs;
- silently install system packages;
- silently modify shell startup files.

---

## 19. Lifecycle events

The loader SHALL emit runtime events for:

```text
runtime.profile.discovered
runtime.profile.selected
runtime.profile.loaded
runtime.profile.initializing
runtime.profile.initialized
runtime.profile.activating
runtime.profile.active
runtime.profile.degraded
runtime.profile.load_failed
runtime.profile.initialization_failed
runtime.profile.activation_failed
runtime.profile.shutdown_started
runtime.profile.shutdown_complete
```

Event payloads SHALL reference typed contract IDs and SHALL NOT include secrets.

---

## 20. Fallback profile

A generic fallback profile SHALL always exist.

Fallback profile properties:

```text
id: generic
kind: generic
platform: unknown or detected platform
capabilities: minimum safe capabilities only
adapters: none unless explicitly safe
providers: passive configuration only
gpu: CPU fallback only
state: ready or degraded
```

Fallback rules:

- Missing Omarchy SHALL NOT prevent Station startup.
- Failed profile activation SHALL fall back when possible.
- Fallback activation SHALL be visible in doctor output.

---

## 21. Omarchy-specific loader interpretation

Omarchy SHALL be represented as a normal runtime profile manifest.

Suggested profile ID:

```text
omarchy
```

Suggested kind:

```text
desktop
```

Omarchy profile detection MAY consider:

```text
Hyprland session indicators
Wayland environment
Arch/pacman indicators
Omarchy-specific config/package markers
notification daemon availability
wl-copy/wl-paste availability
local provider endpoints
GPU tooling
```

Omarchy profile detection SHALL NOT be required for Station startup.

---

## 22. Loader qualification tests

Required tests:

```text
test_manifest_discovery_side_effect_free
test_explicit_profile_selection_wins
test_disabled_profile_never_selected
test_missing_required_capability_rejected
test_fallback_profile_selected_when_no_candidate
test_manifest_validation_rejects_bad_contract_version
test_load_does_not_activate_profile
test_initialize_produces_immutable_contracts
test_activation_publishes_contracts_only
test_activation_fails_closed_on_invalid_contract
test_shutdown_best_effort
test_profile_cannot_write_receipts
test_profile_cannot_change_station_policy
test_omarchy_absent_falls_back_cleanly
test_omarchy_present_selects_omarchy_when_allowed
```

---

## 23. Swarm decomposition lanes

### Lane A — Manifest and loader contracts

Deliver:

```text
RuntimeProfileManifest
RuntimeProfileDependency
RuntimeProfileDetectionSpec
RuntimeProfilePermissionSpec
RuntimeProfileLifecycleSpec
RuntimeProfileSelectionRequest
RuntimeProfileSelectionResult
```

Exit criteria:

```text
contracts serialize deterministically
invalid manifests fail validation
no Station imports in contracts
```

### Lane B — Loader implementation

Deliver:

```text
RuntimeProfileLoader
discover_manifests
select_profile
load
initialize
activate
shutdown
```

Exit criteria:

```text
fallback profile works
profile lifecycle state machine enforced
activation only publishes immutable contracts
```

### Lane C — Lifecycle event emission

Deliver:

```text
runtime.profile.* events
payload validation
secret redaction tests
```

Exit criteria:

```text
events emitted in correct order
failed phases produce RuntimeIssue records
no secrets serialized
```

### Lane D — Ownership boundary tests

Deliver:

```text
receipt-write prohibition test
Station policy mutation prohibition test
verifier mutation prohibition test
approval bypass prohibition test
provider credential mutation prohibition test
```

Exit criteria:

```text
profile cannot gain Station authority through loader
```

### Lane E — Omarchy loader fixture

Deliver:

```text
fake Omarchy manifest
fake Hyprland/Wayland markers
generic Linux degraded fixture
real-host optional marker tests
```

Exit criteria:

```text
Omarchy fixture selected when allowed
generic fallback selected when absent or disabled
```

---

## 24. Global acceptance gate

The profile loader contract is complete when:

```text
canonical loader interface exists
manifest contract exists
selection contract exists
lifecycle state machine exists
ownership boundaries are documented and tested
fallback profile exists
loader health is reported
activation publishes immutable contracts only
Omarchy can be represented without Station-specific branches
Station starts when Omarchy is missing
Station starts when profile loading fails and fallback is available
all loader qualification tests pass
```

---

## 25. Implementation rule

The Runtime Profile Loader is an isolation boundary.

Any implementation that makes Omarchy work by adding Omarchy-specific behavior to Station core SHALL be rejected.

Any implementation that makes the generic profile loader stronger while preserving Station authority boundaries SHALL be preferred.
