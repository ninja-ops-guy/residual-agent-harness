"""Every active probe requires the real namespace boundary; never host fallback.

The result's retained stdout digest must match the authored probe marker. A
missing marker is UNKNOWN, not evidence that the attempted attack was denied.
No process test creates more than eight children. No host process is signalled.
"""
import hashlib
import json
import os
import socket
import pytest


PROBES = {
    "proc_host_root": """
attempted = True
try:
    open('/proc/1/root' + sentinel, 'rb').read(1)
except OSError:
    verdict = 'denied'
else:
    verdict = 'exposed'
""",
    "dev_host_devices": """
attempted = True
verdict = 'denied'
for path in ('/dev/mem', '/dev/kmem', '/dev/sda', '/dev/kmsg'):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        continue
    os.close(fd)
    verdict = 'exposed'
""",
    "namespace_nesting": """
import subprocess
attempted = True
p = subprocess.run(['/usr/bin/unshare', '--user', '--map-root-user', '--mount', '--', '/usr/bin/true'], timeout=2)
verdict = 'denied' if p.returncode else 'contained'
""",
    "unix_host_socket": """
import socket
attempted = True
s = socket.socket(socket.AF_UNIX); s.settimeout(.3)
try:
    s.connect(host_socket)
except OSError:
    verdict = 'denied'
else:
    verdict = 'exposed'
finally:
    s.close()
""",
    "inherited_descriptors": """
attempted = True
verdict = 'denied'
for fd in range(3, 256):
    try:
        os.fstat(fd)
    except OSError:
        continue
    verdict = 'exposed'
""",
    "environment_poisoning": """
attempted = True
verdict = 'exposed' if any(k in os.environ for k in ('TRUST_PARENT_SECRET', 'PYTHONPATH', 'LD_PRELOAD', 'GIT_CONFIG_COUNT')) else 'denied'
""",
    "self_signal_and_process_group": """
import signal
attempted = True
child = os.fork()
if child == 0:
    os.setsid()
    os.kill(os.getpid(), signal.SIGTERM)
    os._exit(92)
pid, status = os.waitpid(child, 0)
verdict = 'contained' if pid == child and os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGTERM else 'exposed'
""",
    "bounded_eight_children": """
attempted = True
children = []
try:
    for _ in range(8):
        child = os.fork()
        if child == 0:
            os._exit(0)
        children.append(child)
except OSError:
    pass
for child in children:
    os.waitpid(child, 0)
verdict = 'contained' if children else 'denied'
""",
    "oversized_filename": """
attempted = True
try:
    open('/tmp/' + 'x' * 300, 'wb').close()
except OSError:
    verdict = 'denied'
else:
    verdict = 'exposed'
""",
    "bounded_sparse_file": """
attempted = True
with open('/tmp/sparse-probe', 'wb') as f:
    f.seek(1024 * 1024); f.write(b'x')
verdict = 'contained' if os.stat('/tmp/sparse-probe').st_size == 1024 * 1024 + 1 else 'exposed'
""",
    "private_device_node": """
import stat
attempted = True
try:
    os.mknod('/tmp/private-null', stat.S_IFCHR | 0o600, os.makedev(1, 3))
except OSError:
    verdict = 'denied'
else:
    verdict = 'contained'
""",
    "readonly_bind_remount": """
import ctypes
attempted = True
libc = ctypes.CDLL(None, use_errno=True)
rc = libc.mount(None, os.getcwd().encode(), None, ctypes.c_ulong(4096 | 32), None)
if rc:
    verdict = 'denied'
else:
    try:
        open('candidate.txt', 'wb').write(b'modified-by-remount')
    except OSError:
        verdict = 'denied'
    else:
        verdict = 'exposed'
""",
    "candidate_executable_replacement": """
attempted = True
try:
    os.replace('/tmp/replacement', 'verifier-entry.py')
except OSError:
    verdict = 'denied'
else:
    verdict = 'exposed'
""",
}


@pytest.mark.parametrize("probe", sorted(PROBES))
def test_bounded_namespace_probe(api, request, tmp_path, monkeypatch, record_property, probe):
    record_property("probe", probe)
    record_property("injection_observed", "false")
    record_property("verdict", "UNKNOWN")
    if not request.config.getoption("--run-bounded-sandbox"):
        pytest.skip("sandbox probes opt in with --run-bounded-sandbox; no attack attempted")
    sandbox = api("residual.factory.m4_sandbox", "probe_isolation", "run_isolated")
    available, reason = sandbox.probe_isolation()
    record_property("prerequisite", reason)
    if not available:
        pytest.skip(f"isolation unavailable ({reason}); no attack attempted")
    work = tmp_path / "work"; work.mkdir()
    (work / "candidate.txt").write_bytes(b"original")
    (work / "verifier-entry.py").write_bytes(b"original-executable")
    sentinel = tmp_path / "sentinel"; sentinel.write_bytes(b"outside-intact")
    host_socket = str(tmp_path / "host.sock")
    server = socket.socket(socket.AF_UNIX); server.bind(host_socket); server.listen(1)
    inherited = os.open(sentinel, os.O_RDONLY); os.set_inheritable(inherited, True)
    monkeypatch.setenv("TRUST_PARENT_SECRET", "test-only-not-a-real-secret")
    monkeypatch.setenv("PYTHONPATH", "/nonexistent-trust-poison")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "999")
    prelude = f"import os\nsentinel={str(sentinel)!r}\nhost_socket={host_socket!r}\n"
    # This source is a bounded, authored test, not an arbitrary supplied payload.
    prelude += "open('/tmp/replacement', 'wb').write(b'replaced')\nattempted=False\nverdict='error'\n"
    script = prelude + PROBES[probe] + f"\nprint('PROBE:{probe}:' + verdict + ':' + str(attempted))\n"
    try:
        outcome = sandbox.run_isolated(("/usr/bin/python3", "-c", script), work,
                                       timeout_s=4., output_limit=8192, memory_mb=128, cpu_s=2.)
    finally:
        os.close(inherited); server.close()
    record_property("runner_status", outcome.status)
    record_property("runner_reason", outcome.reason)
    record_property("stdout_sha256", outcome.stdout_sha256)
    verdict = None
    for value in ("denied", "contained", "exposed"):
        marker = f"PROBE:{probe}:{value}:True\n".encode()
        if outcome.stdout_sha256 == hashlib.sha256(marker).hexdigest():
            verdict = value
    if verdict is None or outcome.status != "pass":
        pytest.fail(f"UNKNOWN probe completion; {probe}: {outcome.status}/{outcome.reason}; no recognized execution marker")
    record_property("injection_observed", "true")
    record_property("verdict", verdict.upper())
    assert sentinel.read_bytes() == b"outside-intact"
    assert verdict != "exposed", f"boundary violation observed: {probe}"
    assert (work / "candidate.txt").read_bytes() == b"original"
    assert (work / "verifier-entry.py").read_bytes() == b"original-executable"
