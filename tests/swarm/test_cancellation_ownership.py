"""Cancellation ownership regressions: real descendants and fail-closed probes."""
import asyncio
import os
from pathlib import Path
import signal
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from residual.runtime import CancellationBudget, CancellationController


@pytest.mark.skipif(sys.platform != "linux", reason="Linux process-group qualification")
def test_exited_leader_does_not_hide_live_descendant(tmp_path):
    async def scenario():
        ready = tmp_path / "child-ready"
        child = (
            "import signal,time; from pathlib import Path; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            f"Path({str(ready)!r}).write_text('ready'); time.sleep(60)"
        )
        parent = (
            "import subprocess,sys,time; from pathlib import Path\n"
            f"p=subprocess.Popen([sys.executable,'-c',{child!r}], "
            "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            f"while not Path({str(ready)!r}).exists(): time.sleep(0.01)\n"
            "print(p.pid, flush=True)\n"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", parent, start_new_session=True,
            stdout=asyncio.subprocess.PIPE)
        controller = CancellationController(CancellationBudget(2.0))
        controller.track_process(process, name="worker", process_group_id=process.pid)
        try:
            child_pid = int(await asyncio.wait_for(process.stdout.readline(), 5))
            await asyncio.wait_for(process.wait(), 5)
            assert process.returncode == 0
            assert controller._group_has_live_members(process.pid)
            assert controller.active_processes == ("worker",)
            report = await controller.abort()
            assert report.cancelled and report.descendants_clean
            assert report.propagated == 1
            assert dict(report.process_outcomes)["worker"] == "killed_group"
            stat = Path(f"/proc/{child_pid}/stat")
            own_stat = Path("/proc/self/stat").read_text()
            if int(own_stat.split(" ", 1)[0]) == os.getpid() and stat.exists():
                assert stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
            # Group liveness also works when /proc belongs to another namespace.
            assert not controller._group_has_live_members(process.pid)
            assert controller.active_processes == ()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await asyncio.wait_for(process.wait(), 5)

    asyncio.run(scenario())


def test_unreadable_proc_cannot_prove_empty_group():
    class UnreadableProcess:
        name = "123"
        def __truediv__(self, _name):
            return self
        def read_text(self):
            raise PermissionError("process inspection denied")

    with patch.object(Path, "is_dir", return_value=True), \
            patch.object(Path, "read_text", return_value=f"{os.getpid()} (test) R 1 {os.getpgrp()} 1"), \
            patch.object(Path, "iterdir", return_value=iter([UnreadableProcess()])), \
            patch("residual.runtime.cancellation.os.killpg", return_value=None) as probe:
        assert CancellationController._group_has_live_members(999)
        probe.assert_called_once_with(999, 0)


def test_foreign_proc_namespace_uses_process_api():
    with patch.object(Path, "is_dir", return_value=True), \
            patch.object(Path, "read_text", return_value="999999999 (foreign) R 1 1 1"), \
            patch.object(Path, "iterdir") as scan, \
            patch("residual.runtime.cancellation.os.killpg", side_effect=ProcessLookupError) as probe:
        assert not CancellationController._group_has_live_members(999)
        scan.assert_not_called()
        probe.assert_called_once_with(999, 0)


@pytest.mark.skipif(os.name != "posix", reason="POSIX group ownership validation")
def test_process_group_registration_requires_dedicated_session_leader():
    controller = CancellationController(CancellationBudget(1))
    process = SimpleNamespace(pid=321, returncode=None)

    with patch("residual.runtime.cancellation.os.getpgid", return_value=321), \
            patch("residual.runtime.cancellation.os.getsid", return_value=321):
        controller.track_process(process, name="owned", process_group_id=321)
    assert controller._processes["owned"] == (process, 321)

    other = SimpleNamespace(pid=400, returncode=None)
    with pytest.raises(ValueError, match="must equal"):
        controller.track_process(other, name="wrong-id", process_group_id=401)

    with patch("residual.runtime.cancellation.os.getpgid", return_value=500), \
            patch("residual.runtime.cancellation.os.getsid", return_value=777), \
            pytest.raises(ValueError, match="dedicated POSIX session"):
        controller.track_process(SimpleNamespace(pid=500, returncode=None),
                                 name="foreign-session", process_group_id=500)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_cancellation_requires_finite_deadline(value):
    with pytest.raises(ValueError):
        CancellationBudget(value)


def test_process_name_cannot_replace_an_owned_process():
    controller = CancellationController(CancellationBudget(1))
    first, second = object(), object()
    controller.track_process(first, name="worker")
    with pytest.raises(ValueError, match="already tracked"):
        controller.track_process(second, name="worker")
    assert controller._processes["worker"][0] is first


def test_task_name_cannot_replace_an_active_operation():
    async def scenario():
        controller = CancellationController(CancellationBudget(1))
        first = asyncio.create_task(asyncio.Event().wait())
        second = asyncio.create_task(asyncio.Event().wait())
        try:
            controller.track(first, name="worker")
            with pytest.raises(ValueError, match="already tracked"):
                controller.track(second, name="worker")
            report = await controller.abort()
            assert report.cancelled and report.propagated == 1
            assert first.cancelled()
        finally:
            first.cancel(); second.cancel()
            await asyncio.gather(first, second, return_exceptions=True)
    asyncio.run(scenario())


def test_old_task_callback_cannot_erase_its_replacement():
    async def scenario():
        controller = CancellationController(CancellationBudget(1))
        first = asyncio.create_task(asyncio.sleep(0))
        second = asyncio.create_task(asyncio.Event().wait())
        # The replacement callback runs before the controller's old cleanup.
        first.add_done_callback(lambda _: controller.track(second, name="worker"))
        controller.track(first, name="worker")
        try:
            await first
            assert controller.active == ("worker",)
            report = await controller.abort()
            assert report.cancelled and report.propagated == 1
            assert second.cancelled()
        finally:
            second.cancel()
            await asyncio.gather(second, return_exceptions=True)
    asyncio.run(scenario())
