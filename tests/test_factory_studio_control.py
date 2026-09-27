import tempfile, unittest
from pathlib import Path
from residual.factory.studio_control import AuthoritativeStudioControl, StudioControlError

DOC={"intent":"demo","requirements":[{"id":"R1","text":"write output","acceptance":{"checks":["exists"]}}]}

class StudioControlTests(unittest.TestCase):
 def test_plan_and_exact_hash_approval(self):
  with tempfile.TemporaryDirectory() as td:
   c=AuthoritativeStudioControl(td);p=c.control("plan",{"document":DOC});self.assertEqual(p["status"],"draft")
   with self.assertRaises(StudioControlError):c.control("approve",{"plan_hash":"0"*64,"approved_by":"operator"})
   a=c.control("approve",{"plan_hash":p["graph_hash"],"approved_by":"operator"});self.assertEqual(a["status"],"approved")
 def test_run_and_integrate_fail_closed_without_authoritative_inputs(self):
  with tempfile.TemporaryDirectory() as td:
   c=AuthoritativeStudioControl(td);p=c.control("plan",{"document":DOC})
   for action in ("run","integrate"):
    with self.assertRaises(StudioControlError):c.control(action,{"plan_hash":p["graph_hash"]})
if __name__=="__main__":unittest.main()
