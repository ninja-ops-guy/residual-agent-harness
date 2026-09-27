"""Native Windows C01/C02/CV-06 ownership qualification.

Concurrency and lifecycle tests in this module are native evidence only when
``os.name == "nt"``. API fault injection is deliberately labelled separately.
No public listener, provider, credential, or production service is used.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest import mock

from residual.core import ContractError, canonical
from residual.station import ownership, server, service
from residual.station.ownership import StationDataDirOwnership, StationOwnershipError


WINDOWS = os.name == "nt"
ROUNDS = 20
CLEAN_CHURN = 100
CRASH_CHURN = 100


CONTENDER = textwrap.dedent(r"""
    import pathlib, sys, time
    from residual.station.ownership import StationDataDirOwnership, StationOwnershipError
    root, gate, hold = sys.argv[1], pathlib.Path(sys.argv[2]), float(sys.argv[3])
    deadline = time.monotonic() + 15
    while not gate.exists():
        if time.monotonic() >= deadline:
            print("ORCHESTRATION_TIMEOUT", flush=True); raise SystemExit(91)
        time.sleep(.002)
    try:
        owner = StationDataDirOwnership(root)
    except StationOwnershipError:
        print("REJECT", flush=True); raise SystemExit(23)
    print("OWNER", flush=True)
    time.sleep(hold)
    owner.close()
""")

HOLDER = textwrap.dedent(r"""
    import sys, time
    from residual.station.ownership import StationDataDirOwnership
    owner = StationDataDirOwnership(sys.argv[1])
    print("READY", flush=True)
    time.sleep(60)
""")

CLEAN_HOLDER = textwrap.dedent(r"""
    import pathlib, sys, time
    from residual.station.ownership import StationDataDirOwnership
    owner = StationDataDirOwnership(sys.argv[1])
    release = pathlib.Path(sys.argv[2])
    print("READY", flush=True)
    deadline = time.monotonic() + 30
    while not release.exists():
        if time.monotonic() >= deadline: raise SystemExit(91)
        time.sleep(.01)
    owner.close()
    print("CLOSED", flush=True)
""")


@unittest.skipUnless(WINDOWS, "native Windows qualification")
class NativeWindowsOwnershipQualification(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "ResidualState"
        self.addCleanup(self.temp.cleanup)
        self.env = mock.patch.dict(os.environ, {
            "RESIDUAL_REMOTE_EXPOSURE": "", "RESIDUAL_ALLOWED_HOSTS": "",
            "RESIDUAL_PUBLIC_URL": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_contender(self, root=None):
        gate = Path(self.temp.name) / f"gate-{time.time_ns()}"
        gate.touch()
        return subprocess.run(
            [sys.executable, "-c", CONTENDER, str(root or self.root), str(gate), "0"],
            capture_output=True, text=True, timeout=15,
        )

    def start_holder(self):
        process = subprocess.Popen(
            [sys.executable, "-c", HOLDER, str(self.root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.addCleanup(self.stop_process, process)
        self.assertEqual(process.stdout.readline().strip(), "READY")
        return process

    @staticmethod
    def stop_process(process):
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

    def assert_rejected_process(self):
        result = self.run_contender()
        self.assertEqual((result.returncode, result.stdout.strip()), (23, "REJECT"), result.stderr)

    def snapshot(self):
        entries = {}
        if self.root.exists():
            for path in sorted(self.root.rglob("*")):
                relative = str(path.relative_to(self.root))
                entries[relative] = ("dir", None) if path.is_dir() else (
                    "file", hashlib.sha256(path.read_bytes()).hexdigest())
        return entries

    def test_w01_same_process_duplicate_and_reacquire(self):
        first = StationDataDirOwnership(self.root)
        with self.assertRaises(StationOwnershipError):
            StationDataDirOwnership(self.root)
        first.close()
        StationDataDirOwnership(self.root).close()

    def test_w02_twenty_round_four_process_race_has_exactly_one_owner(self):
        for round_number in range(ROUNDS):
            gate = Path(self.temp.name) / f"race-{round_number}"
            processes = [subprocess.Popen(
                [sys.executable, "-c", CONTENDER, str(self.root), str(gate), ".20"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            ) for _ in range(4)]
            gate.touch()
            outputs = [process.communicate(timeout=20) for process in processes]
            owners = sum(out.strip() == "OWNER" for out, _ in outputs)
            rejected = sum(out.strip() == "REJECT" for out, _ in outputs)
            self.assertEqual((owners, rejected), (1, 3), (round_number, outputs))

    def test_w03_clean_process_release(self):
        release = Path(self.temp.name) / "clean-release"
        holder = subprocess.Popen(
            [sys.executable, "-c", CLEAN_HOLDER, str(self.root), str(release)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            self.assertEqual(holder.stdout.readline().strip(), "READY")
            self.assert_rejected_process()
            release.touch()
            self.assertEqual(holder.stdout.readline().strip(), "CLOSED")
            holder.wait(timeout=10)
            result = self.run_contender()
            self.assertEqual((result.returncode, result.stdout.strip()), (0, "OWNER"), result.stderr)
        finally:
            self.stop_process(holder)

    def test_w04_crash_process_death_release(self):
        holder = self.start_holder()
        self.assert_rejected_process()
        holder.kill(); holder.wait(timeout=10)
        deadline = time.monotonic() + 10
        while True:
            result = self.run_contender()
            if result.returncode == 0:
                break
            self.assertLess(time.monotonic(), deadline, result.stderr)
            time.sleep(.02)

    def test_w05_closing_reservation_retains_owner(self):
        station = service.Station(self.root)
        reservation = station._lifecycle.reserve()
        with self.assertRaisesRegex(ContractError, "ownership retained"):
            station.close(timeout=.02)
        self.assertEqual(station._lifecycle._state, "CLOSING")
        self.assert_rejected_process()
        reservation.cancel()
        station.close(timeout=1)
        self.assertEqual(self.run_contender().returncode, 0)

    def test_w06_background_work_retains_owner(self):
        station = service.Station(self.root)
        entered, release = threading.Event(), threading.Event()
        def work(_progress):
            entered.set()
            self.assertTrue(release.wait(10))
            return {"ok": True}
        station.launch("windows-qualification", work)
        self.assertTrue(entered.wait(5))
        with self.assertRaisesRegex(ContractError, "ownership retained"):
            station.close(timeout=.02)
        self.assert_rejected_process()
        with self.assertRaises(ContractError):
            station.create(service.demo_spec(), demo=True)
        release.set()
        deadline = time.monotonic() + 10
        while station.active and time.monotonic() < deadline:
            time.sleep(.01)
        station.close(timeout=2)
        self.assertEqual(self.run_contender().returncode, 0)

    def test_w07_server_lifetime_retains_owner(self):
        station = service.Station(self.root)
        http = server.Server(("127.0.0.1", 0), station)
        try:
            with self.assertRaisesRegex(ContractError, "ownership retained"):
                station.close(timeout=0)
            self.assert_rejected_process()
        finally:
            http.server_close()
        station.close(timeout=1)
        self.assertEqual(self.run_contender().returncode, 0)

    def test_w08_server_constructor_failure_cleans_reservation(self):
        station = service.Station(self.root)
        with mock.patch.object(server.ThreadingHTTPServer, "__init__", side_effect=OSError("bind denied")):
            with self.assertRaises(OSError):
                server.Server(("127.0.0.1", 0), station)
        station.close(timeout=0)
        self.assertEqual(self.run_contender().returncode, 0)

    def test_w09_exposure_rejected_before_bind_and_localhost_normalized(self):
        station = service.Station(self.root)
        with mock.patch.object(server.ThreadingHTTPServer, "__init__") as bind:
            for host in ("0.0.0.0", "qualification.invalid"):
                with self.subTest(host=host), self.assertRaises(ContractError):
                    server.Server((host, 0), station)
            bind.assert_not_called()
        captured = []
        def intercept(instance, address, handler):
            captured.append(address); instance.server_port = 0
        with mock.patch.object(server.ThreadingHTTPServer, "__init__", intercept), \
             mock.patch.object(server.Server, "_register_legacy_worker_key"):
            http = server.Server(("localhost", 0), station)
            self.assertEqual(captured, [("127.0.0.1", 0)])
            http._lifetime.cancel()
        station.close()

    def test_w10_path_case_equivalence(self):
        first = StationDataDirOwnership(self.root)
        try:
            alternate = str(self.root).swapcase()
            with self.assertRaises(StationOwnershipError):
                StationDataDirOwnership(alternate)
        finally:
            first.close()

    def test_w11_redundant_components_are_same_domain(self):
        self.root.mkdir(parents=True)
        alternate = self.root / "child" / ".."
        first = StationDataDirOwnership(self.root)
        try:
            with self.assertRaises(StationOwnershipError):
                StationDataDirOwnership(alternate)
        finally:
            first.close()

    def test_w12_clean_and_crash_churn(self):
        for _ in range(CLEAN_CHURN):
            StationDataDirOwnership(self.root).close()
        for iteration in range(CRASH_CHURN):
            holder = subprocess.Popen(
                [sys.executable, "-c", HOLDER, str(self.root)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                self.assertEqual(holder.stdout.readline().strip(), "READY", iteration)
                holder.kill(); holder.wait(timeout=10)
                StationDataDirOwnership(self.root).close()
            finally:
                self.stop_process(holder)

    def test_w13_failed_contenders_do_not_poison_owner_or_registry(self):
        owner = StationDataDirOwnership(self.root)
        for _ in range(25):
            self.assert_rejected_process()
            owner.assert_live()
        owner.close()
        StationDataDirOwnership(self.root).close()

    def test_phase3_denied_station_is_pre_mutation(self):
        station = service.Station(self.root)
        station.store.settings({"windows_qualification": "unchanged"})
        before = self.snapshot()
        settings = station.store.settings()
        with mock.patch.object(service, "Store", wraps=service.Store) as store:
            with self.assertRaises(ContractError):
                service.Station(self.root)
            store.assert_not_called()
        self.assertEqual(station.store.settings(), settings)
        self.assertEqual(self.snapshot(), before)
        station.close()

    def test_phase4_closing_rejects_mutation_surface_without_changes(self):
        station = service.Station(self.root)
        project = station.create(service.demo_spec(), demo=True)["project_id"]
        reservation = station._lifecycle.reserve()
        with self.assertRaises(ContractError):
            station.close(timeout=0)
        before = self.snapshot()
        calls = [
            lambda: station.create(service.demo_spec(), demo=True),
            lambda: station.triage(project),
            lambda: station.prepare(project, "runner"),
            lambda: station.run_one(project),
            lambda: station.rebase_disjoint(project, "OPS-101"),
            lambda: station.review(project, "OPS-101"),
            lambda: station.integrate(project, "OPS-101"),
            lambda: station.batch(project),
            lambda: station.cloud_report(project),
            lambda: station.export(project),
            lambda: station.launch("blocked", lambda _progress: {}),
            lambda: server.Server(("127.0.0.1", 0), station),
        ]
        for call in calls:
            with self.subTest(call=call), self.assertRaises(ContractError):
                call()
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(station.active, set())
        self.assert_rejected_process()
        reservation.cancel()
        station.close()

    def test_native_environment_evidence(self):
        self.assertEqual(os.name, "nt")
        filesystem = ctypes.create_unicode_buffer(261)
        self.assertTrue(ctypes.windll.kernel32.GetVolumeInformationW(
            self.root.anchor, None, 0, None, None, None,
            filesystem, len(filesystem)))
        evidence = {
            "os_name": os.name, "windows": platform.platform(),
            "python": sys.version, "architecture": platform.machine(),
            "username": os.environ.get("USERNAME"),
            "elevated": bool(ctypes.windll.shell32.IsUserAnAdmin()),
            "filesystem": filesystem.value,
        }
        print("WINDOWS_NATIVE_EVIDENCE=" + canonical(evidence))

    def test_w15_global_namespace_works_in_current_runner_session(self):
        first = StationDataDirOwnership(self.root)
        try:
            self.assert_rejected_process()
            digest = hashlib.sha256(first.key[1].encode("utf-8")).hexdigest()
            name = "Global\\RESIDUAL-Station-" + digest
            kernel = ctypes.windll.kernel32
            open_mutex = kernel.OpenMutexW
            open_mutex.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
            open_mutex.restype = wintypes.HANDLE
            close_handle = kernel.CloseHandle
            close_handle.argtypes = (wintypes.HANDLE,)
            close_handle.restype = wintypes.BOOL
            opened = open_mutex(0x00100000, False, name)  # SYNCHRONIZE
            self.assertTrue(opened, ctypes.get_last_error())
            self.assertTrue(close_handle(opened))
        finally:
            first.close()


@unittest.skipUnless(WINDOWS, "Windows API fault injection; not native concurrency evidence")
class WindowsApiFaultInjection(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def exercise(self, handle, error):
        create = mock.Mock(return_value=handle)
        close = mock.Mock(return_value=True)
        kernel = mock.Mock(CreateMutexW=create, CloseHandle=close)
        with mock.patch.object(ctypes, "WinDLL", return_value=kernel), \
             mock.patch.object(ctypes, "set_last_error"), \
             mock.patch.object(ctypes, "get_last_error", return_value=error):
            return StationDataDirOwnership(self.temp.name), close

    def test_w14_null_handle_fails_closed(self):
        with self.assertRaises(StationOwnershipError):
            self.exercise(None, 5)

    def test_w14_access_denied_fails_closed(self):
        with self.assertRaises(StationOwnershipError):
            self.exercise(None, 5)

    def test_w14_already_exists_closes_handle_and_rejects(self):
        create = mock.Mock(return_value=123)
        close = mock.Mock(return_value=True)
        kernel = mock.Mock(CreateMutexW=create, CloseHandle=close)
        with mock.patch.object(ctypes, "WinDLL", return_value=kernel), \
             mock.patch.object(ctypes, "set_last_error"), \
             mock.patch.object(ctypes, "get_last_error", return_value=183), \
             self.assertRaises(StationOwnershipError):
            StationDataDirOwnership(self.temp.name)
        close.assert_called_once_with(123)

    def test_w14_unexpected_success_status_closes_handle_and_fails_closed(self):
        create = mock.Mock(return_value=123)
        close = mock.Mock(return_value=True)
        kernel = mock.Mock(CreateMutexW=create, CloseHandle=close)
        with mock.patch.object(ctypes, "WinDLL", return_value=kernel), \
             mock.patch.object(ctypes, "set_last_error"), \
             mock.patch.object(ctypes, "get_last_error", return_value=87), \
             self.assertRaises(StationOwnershipError):
            StationDataDirOwnership(self.temp.name)
        close.assert_called_once_with(123)


if __name__ == "__main__":
    unittest.main(verbosity=2)
