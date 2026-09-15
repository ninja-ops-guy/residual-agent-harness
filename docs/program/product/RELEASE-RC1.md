# v1.0.0-rc1 release criteria

**Status: candidate criteria; no release tag or production-support declaration.**
Baseline `pyproject.toml` is version `0.5.0`, requires Python `>=3.11`, and declares
no mandatory dependencies. Metadata is an installation constraint, not evidence
that every newer interpreter, platform or execution mode is supported.

## Support profiles to qualify

| Profile | RC1 test target | Evidence needed | Current qualification boundary |
| --- | --- | --- | --- |
| Core/Station, source and wheel | Linux x86_64; CPython 3.11, 3.12, 3.13 | Fresh environment import/CLI, scripted workflow, trace binding, Station operator flow | CI declares Ubuntu / these Python versions; inspect exact candidate runs before claiming green |
| Factory M2/M3/M4 | Linux x86_64 / CPython 3.12 on frozen VM image | Optional extras, OS containment and exact accepted/verified tree checks; all #63/#81 gates | Factory workflows target Ubuntu / 3.12; boundary not qualified by this lane |
| Windows/macOS Station/native launchers | Versions/images explicitly selected before RC run | Launch, provider configuration, run/export/restart checks | Launchers exist; broader support is pending retained install-matrix evidence |
| Containers | Pinned image digest and architecture | No privileged fallback; namespace/profile probes inside deployed container, volume durability/restart | Docker availability or root UID alone proves nothing |
| Linux arm64, other Python versions | Experimental until explicitly added | Same applicable matrix and containment evidence | Excluded from initial support claims |

Record VM image digest, distribution, kernel, CPU architecture, libc, SQLite,
Python, Git, libseccomp and optional package versions. Pin concrete image/version
identities before collecting qualification results; `ubuntu-latest` is insufficient
for reproducibility. No platform receives blanket production support because the
scripted core demo passed.

## Install and optional dependency matrix

| Installation | Candidate command / procedure | Required checks |
| --- | --- | --- |
| Source core | `python3 -m residual --help` from checkout | README paths and clean-venv offline demonstration |
| Wheel core | Install exact RC wheel from reviewed wheelhouse with `pip --no-index --find-links` | Run outside checkout; package imports, entry points, static/schema assets, demo and uninstall |
| Factory extras | Install exact RC wheel plus `[factory]` dependency lock | `cryptography>=43`, `PyYAML>=6` declared; capture resolved versions/hashes and Factory tests |
| Marketplace extras | Exact wheel plus `[marketplace]` dependency lock | `cryptography>=43` declared; signature/plugin admission tests |
| All extras | Factory + marketplace union | No dependency conflict or missing package data |
| Offline install | Preassembled wheelhouse, networking blocked | No implicit package/model download; useful missing-dependency error |
| Upgrade | 0.5.0 fixture → RC in backed-up isolated state | Schema compatibility, historical receipt checks, task/HITL recovery, rollback |
| Provider/local model | One explicit cloud provider and one local endpoint on separate runs | Configure, diagnostics, bounded smoke, unavailable/key-error explanation; no silent simulation fallback |

These are installation test targets, not commands executed in this preparation
lane. Core onboarding currently documents source mode and a package-name install;
RC1 must replace any unverified public package availability assumption with tested,
version-specific release instructions.

## Minimum OS isolation capabilities

Current M2 brokered Python execution checks Linux, `libseccomp.so.2`, seccomp filter
loading, `os.pidfd_open` and `signal.pidfd_send_signal`; host file brokers and owned
private runtime directories carry additional boundary responsibilities. This
profile does **not** by itself establish isolated arbitrary verifier execution.

RC1's M4 hostile-verifier profile must probe creation of the required user, mount,
PID and network namespaces, UID/GID mappings, mount-private propagation, restricted
`/proc`/`/dev` views, read-only trusted executable roots, no inherited host sockets
or descriptors, seccomp enforcement and owned process cleanup. Where the selected
implementation uses a privileged helper or supervisor instead of unprivileged user
namespaces, pin and review that trust boundary explicitly. Namespace existence in
`/proc/self/ns` is not proof the current deployment may create or safely configure
it. Add cgroup/resource-limit requirements actually used by the selected profile.

Freeze profile IDs and probe results after #81 stabilizes. A numerical minimum
kernel version is not yet established by retained multi-kernel evidence. Until it
is, fail closed on unavailable capabilities, state the missing probe precisely,
and publish the tested kernel range. Never silently fall back to executing hostile
verifiers on the host to make onboarding pass.

## Release gates (all required unless profile explicitly excluded)

| Gate | Evidence / pass rule |
| --- | --- |
| RC-01 source qualification | Reviewed exact commit/tree; #63 resolved and #81 qualified on merged main; timing nondeterminism classified with retained schedules |
| RC-02 truthful status | #48 traceability reconciled; implementations and tests linked to versioned claims |
| RC-03 install matrix | Every supported profile cell has a retained clean-environment result; excluded cells documented |
| RC-04 receipt compatibility | Inventory `StationReceipt`, `WorkerReceipt`, `IntegrationReceipt`, observations, checkpoints and HITL schema versions; strict readers reject unknown/ambiguous versions |
| RC-05 API contract | Publish supported CLI/API surface, exit codes, PASS/FAIL/UNKNOWN/ERROR mapping, additive changes and breaking-change policy; internal modules excluded explicitly |
| RC-06 state recovery | PROD-007 crash matrix passed for advertised profiles; single-host mode may ship without distributed mode only if exclusions are explicit |
| RC-07 security | Threat model reviewed, sandbox/fuzz/adversarial corpus gates passed; remaining severity/limitations documented against exact candidate |
| RC-08 supply chain | Wheel/sdist/container SBOM including direct/transitive/runtime dependencies, licenses and resolved hashes; vulnerability scan retained and blockers resolved |
| RC-09 reproducible artifact identity | Build commands/tool versions, source SHA/tree, lockfiles, wheel/sdist/container SHA-256; rebuild comparison and any nondeterminism explained |
| RC-10 signatures | Sign release artifact manifest with reviewed identity; independently verify signatures and all hashes on downloaded artifacts |
| RC-11 upgrade/migration | Validated backups, supported upgrade path and tested rollback; no mutation of historical signed receipts; schema-unknown fails closed |
| RC-12 operator onboarding | Blank Linux VM READMEs-only run, clean install, one configured provider/local model, useful diagnostics, scripted demo, recoverable failure explanations |

The existing `residual/supplychain/` helpers are implementation building blocks,
not evidence that a particular release has a complete SBOM, signed artifacts or
passed a scanner. Release logs must show actual generation and independent checks.

## Versioning and known limitations

Receipt schemas and public APIs are versioned separately from the package release.
Never reinterpret old signed bytes under a new schema. Readers accept explicitly
listed historical versions; migrations produce new records with provenance. RC
breaking changes require release notes, a migration example and compatibility
fixture. Stable v1 guarantees begin only for the published supported surface.

Known gaps at this baseline: M4 trust-boundary qualification; distributed fencing
and atomic accepted-head publication; general schema migration; crash recovery
across independent durable stores; physical blank-VM onboarding; full provider and
platform install matrix; no measured production consensus/HA or universal verifier
correctness. Long soak and R0–R5 results must be cited only once retained; an RC tag
alone proves none of them.
