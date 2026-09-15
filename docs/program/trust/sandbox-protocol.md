# Bounded sandbox red-team protocol v1

Run only in a disposable Linux environment authorized for kernel namespace
tests. `run_isolated` is the sole candidate-execution route. If the real
capability probe fails, every payload remains **unattempted / UNKNOWN**. The
suite never uses fixture execution as a replacement for unavailable isolation.

Each probe has a four-second wall clock, two-second requested CPU limit, 128 MiB
per-process address-space limit and 8 KiB combined output cap. The suite creates
at most eight children per probe and reaps them. It never signals a host PID or
process group and never creates an unbounded fork loop. File payloads stay
within roughly 1 MiB; no real disk-full test or physical device write occurs.

| Probe | Concrete injection | Observable oracle | Scope limit |
|---|---|---|---|
| `proc_host_root` | Open external sentinel through `/proc/1/root` | Authored marker says denied; external sentinel unchanged | Does not enumerate every procfs handle or namespace-mount escape |
| `dev_host_devices` | Bounded nonblocking open of mem/kmem/sda/kmsg paths | No descriptor obtained | Does not read/write physical devices |
| `namespace_nesting` | One nested user/mount namespace with `true` | Denial or successful contained command | Nested success alone does not prove safety against all nested operations |
| `unix_host_socket` | Connect to an actual host filesystem Unix socket outside candidate bind | Connection denied | Abstract sockets and adversarial sockets inherited through a broker remain future probes |
| `inherited_descriptors` | Parent opens deliberately inheritable sentinel FD; candidate scans 3..255 | No inherited descriptor visible after bootstrap exec | Does not exercise a malicious broker's explicit FD passing |
| `environment_poisoning` | Parent supplies test secret, poisoned PYTHONPATH and Git config count | Candidate contains none of these variables | No real secrets used; LD_PRELOAD absence checked without loading a hostile host library |
| `self_signal_and_process_group` | One child creates its own session then signals itself | Reaped SIGTERM child | Does not claim escaped-descendant cleanup after parent exit |
| `bounded_eight_children` | At most eight forks, each exits and is reaped | Children completed or fork denied | Not a fork bomb or resource-exhaustion proof |
| `oversized_filename` | 300-character basename in scratch | Name rejected | Single filesystem's limit only |
| `bounded_sparse_file` | Logical hole plus one byte, about 1 MiB | Exact logical size in sandbox scratch | No multi-gigabyte sparse-file or aggregate storage test |
| `private_device_node` | Try private `/tmp` null device node (1,3) | Denied or creation contained in private tmpfs | Does not establish safety of arbitrary device major/minor access |
| `readonly_bind_remount` | Try clearing read-only on candidate bind, then modify fixture file | Operation denied and original host fixture bytes unchanged | Critical TRUST-001 gate; needs live capable host |
| `candidate_executable_replacement` | Try replace candidate entry script from sandbox scratch | Replacement denied and original bytes unchanged | Toolchain executable swap, bind-mount path collision and pre-exec race remain future probes |

Host-side `test_toctou_leaf_swap_is_actually_injected_and_never_follows_link`
performs deterministic mutation between validation and replacement. It asserts
that the substitution actually occurred and that no external sentinel bytes
changed. This supplements namespace probes without executing untrusted host
code.

## Result classification

The authored script emits one exact `PROBE:<name>:<verdict>:True` marker after
its attempted operation. The retained runner stdout SHA-256 must match that
marker and the process must have completed normally. Missing/ambiguous markers,
timeouts or infrastructure errors are **UNKNOWN completion**, which fails the
test gate; they are never interpreted as containment. JUnit records the
prerequisite, runner outcome, stdout digest and whether injection was observed.

`DENIED` and `CONTAINED` apply only to the specific attempted operation and its
oracle. `EXPOSED` fails the test. Candidate-file and outside-sentinel equality
are checked independently on the host after execution. Marker content alone
does not constitute a general security proof.

## Explicit remaining work

Deterministic parent-directory rename during descriptor traversal; snapshot
read races with same-size restoration; abstract Unix sockets; inherited
directory descriptors from a broker; descendant liveness after namespace-init
death; nested namespace mount attacks; toolchain replacement races; aggregate
cgroup PID/memory budgets; output-channel spoofing; kernel-version matrix.
These items are designed coverage obligations, not claimed passing tests.
