import gc
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from residual.station import ownership as mod


@unittest.skipUnless(os.name == "posix", "POSIX lock-shape/fork controls; not Windows qualification")
class ExtraOwnershipTests(unittest.TestCase):
    def test_failed_contender_does_not_remove_live_owner_registry(self):
        with tempfile.TemporaryDirectory() as td:
            first=mod.StationDataDirOwnership(td)
            try:
                for _ in range(3):
                    with self.assertRaises(mod.StationOwnershipError): mod.StationDataDirOwnership(td)
                    gc.collect()
                    self.assertIn(first.key, mod.StationDataDirOwnership._owned)
            finally: first.close()

    def test_hardlinked_lock_is_rejected_without_mutating_target(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'root';root.mkdir();outside=Path(td)/'preserved'
            outside.write_text('preserve me')
            os.link(outside, root/'.residual-station-owner.lock')
            with self.assertRaises(mod.StationOwnershipError):
                owner=mod.StationDataDirOwnership(root);owner.close()
            self.assertEqual(outside.read_text(),'preserve me')

    def test_fifo_lock_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            os.mkfifo(Path(td)/'.residual-station-owner.lock')
            with self.assertRaises(mod.StationOwnershipError): mod.StationDataDirOwnership(td)

    def test_acquisition_never_truncates_existing_lock(self):
        with tempfile.TemporaryDirectory() as td:
            lock=Path(td)/'.residual-station-owner.lock';lock.write_text('diagnostic bytes')
            with mod.StationDataDirOwnership(td): self.assertEqual(lock.read_text(),'diagnostic bytes')
            self.assertEqual(lock.read_text(),'diagnostic bytes')

    def test_forked_child_close_cannot_unlock_parent(self):
        with tempfile.TemporaryDirectory() as td:
            owner=mod.StationDataDirOwnership(td)
            try:
                pid=os.fork()
                if pid==0:
                    try:
                        owner.close()
                        os._exit(0)
                    except BaseException: os._exit(9)
                _,status=os.waitpid(pid,0)
                self.assertEqual(os.waitstatus_to_exitcode(status),0)
                # A clean exec child does not inherit the process-local guard.
                import subprocess,sys
                command="from residual.station.ownership import StationDataDirOwnership; import sys; StationDataDirOwnership(sys.argv[1])"
                run=subprocess.run([sys.executable,'-c',command,td],capture_output=True,timeout=5)
                self.assertNotEqual(run.returncode,0)
            finally: owner.close()

    def test_closed_owner_rejected_by_assertion(self):
        with tempfile.TemporaryDirectory() as td:
            owner=mod.StationDataDirOwnership(td);owner.close()
            with self.assertRaises(mod.StationOwnershipError):owner.assert_live()

if __name__=='__main__':unittest.main()
