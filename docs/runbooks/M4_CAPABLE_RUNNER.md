# M4 Capable-Runner Preflight — Operator Runbook

## Qualification boundary statement

- A **BLOCKED** preflight report is **not** qualification. It is a precise
  statement of which capabilities are missing.
- A **skipped** test is **not** qualification. `M4_REQUIRE_ISOLATION=1`
  exists so the qualification lane fails loudly instead of skipping.
- Only `verdict: QUALIFIED` from `scripts/m4_runner_preflight.py` **on the
  runner that will execute the M4 lane**, followed by the isolated test
  suite actually executing (not skipping), counts as qualification evidence.
- This preflight **unblocks but does not replace** draft PR #88
  ("ci: require actual M4 execution before qualification"): #88 wires the
  gate into CI; this probe defines what "capable runner" means.

## Running the probe

```sh
python3 scripts/m4_runner_preflight.py --runs-dir runs --output preflight-report.json
echo $?   # 0 = QUALIFIED, 3 = BLOCKED
```

Output is a JSON report with deterministic capability ordering and a
`capability_hash` (SHA-256 over the canonical capabilities mapping only —
no timestamps), so two runners with identical capability states produce
identical hashes.

### Reading the report

- `capabilities.<name>.status`: `PASS` (proven by a real execution probe),
  `FAIL` (required resource absent/malformed), `BLOCKED` (kernel or
  environment refused it at runtime).
- `capabilities.<name>.detail`: machine-readable evidence, e.g.
  `userns_exec_probe_rc=1:unshare: unshare failed: Operation not permitted`.
- `capabilities.<name>.remediation`: the operator action.
- `blocked`: sorted list of every capability that is not PASS.
- `verdict`: `QUALIFIED` iff `blocked` is empty.

## Wiring the fail-loudly lane

```sh
# Qualification lane: any BLOCKED capability turns the namespace-dependent
# tests in tests/test_factory_m4_sandbox.py into loud failures that embed
# the preflight report. Default (unset) keeps skip-with-reason dev behavior.
M4_REQUIRE_ISOLATION=1 python3 -m unittest tests.test_factory_m4_sandbox
```

Recommended CI shape: run the probe first; if exit 3, upload the JSON
report as an artifact and fail the lane. Do not mark the lane green on
skips.

## Per-capability remediation

| Capability | What PASS requires | Common remediation |
|---|---|---|
| `user_namespace` | `unprivileged_userns_clone=1` (if present), `max_user_namespaces>0`, and `unshare --user --map-root-user true` exits 0 | `sysctl -w kernel.unprivileged_userns_clone=1 user.max_user_namespaces=15000`; persist in `/etc/sysctl.d/`. Kernel needs `CONFIG_USER_NS=y`. In containers, the runtime must not seccomp-deny `unshare`. |
| `mount_namespace` | `unshare --user --map-root-user --mount true` exits 0 | Fix userns first. Docker: default seccomp allows it; custom profiles may not (`CLONE_NEWNS`). |
| `pid_namespace` | `--pid --fork --kill-child` probe exits 0 | `CONFIG_PID_NS=y`; nested containers often deny it — run the lane on a VM runner or privileged-enough container. |
| `ipc_namespace` | `--ipc` probe exits 0 | `CONFIG_IPC_NS=y`. |
| `uts_namespace` | `--uts` probe exits 0 | `CONFIG_UTS_NS=y`. |
| `net_namespace` | `--net` probe exits 0 | `CONFIG_NET_NS=y`. |
| `seccomp` | `/proc/self/status` has a `Seccomp:` field and `filter` appears in `/proc/sys/kernel/seccomp/actions_avail` | Kernel `CONFIG_SECCOMP_FILTER=y`. gVisor/sandboxed containers that hide filter support cannot qualify. |
| `cgroups_v2` | `/sys/fs/cgroup/cgroup.controllers` exists and `cgroup.subtree_control` is writable | Boot with unified hierarchy (`systemd.unified_cgroup_hierarchy=1`). Delegate a sub-tree: systemd unit `Delegate=yes`, or chown the delegated cgroup dir to the runner user. Docker: needs a cgroup2 host. |
| `bubblewrap` | `bwrap` on PATH and `bwrap --ro-bind / / -- /bin/true` exits 0 | Debian/Ubuntu: `apt install bubblewrap`. Fedora/RHEL: `dnf install bubblewrap`. If the exec probe fails but userns passes, use the setuid build where policy permits. |
| `pidfd` | `os.pidfd_open` exists and a live call succeeds | Python ≥ 3.9, kernel ≥ 5.3, and a seccomp profile that permits `pidfd_open` (Docker ≥ 20.10 default profile does). |
| `af_unix` | bind/listen on a socket in a private tmp dir | `CONFIG_UNIX=y`; check LSM/seccomp policy. |
| `artifact_retention` | `runs/` writable, write+fsync succeeds, free space ≥ threshold (default 64 MiB) | Mount the evidence volume read-write; free space or pass `--min-free-bytes`. |

## Rerunning

The probe is read-only except for a small fsync probe file inside
`--runs-dir`, which is removed immediately. It is safe and deterministic to
rerun; compare `capability_hash` before/after remediation to confirm exactly
which capabilities changed state.

## Common CI images

- **GitHub `ubuntu-latest` hosted runners**: userns/mount/pid/ipc/uts/net
  probes pass; `bwrap` needs `sudo apt install bubblewrap`; cgroup v2
  delegation requires a writable sub-cgroup.
- **Docker `python:*` containers**: `unshare` is present but namespace
  creation typically needs `--cap-add SYS_ADMIN` or a permissive seccomp
  profile; cgroup v2 requires a cgroup2 host; `bwrap` is not installed by
  default.
- **gVisor / runsc sandboxed containers**: seccomp filter availability and
  some namespaces are typically BLOCKED; these runners cannot qualify.
