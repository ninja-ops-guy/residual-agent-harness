import unittest
from dataclasses import replace
from residual.vector_wirepod import *
class T:
 def call(self,n,a): return {"ok":True}
class Tests(unittest.TestCase):
 def setUp(self): self.p=CapabilityPolicy(frozenset({"vector.speak","vector.observe"}),2,10)
 def spec(self): return BehaviorSpec("greet","candidate",("vector.speak",),{"said":True},{"wirepod":"test","mcp":"v1","robot":"test"})
 def test_unknown_tool_fails_closed(self):
  with self.assertRaises(PolicyViolation): GuardedVectorSession(T(),self.p).call("vector.shell",{})
 def test_budget(self):
  s=GuardedVectorSession(T(),self.p); s.call("vector.speak",{}); s.call("vector.speak",{})
  with self.assertRaises(PolicyViolation): s.call("vector.speak",{})
 def test_no_probe_no_acceptance(self): self.assertFalse(VectorQualifier(self.p).qualify(self.spec(),[lambda _:True]).accepted)
 def test_forbidden_skips_tests(self):
  ran=[]; r=VectorQualifier(self.p).qualify(replace(self.spec(),required_tools=("vector.shell",)),[lambda _:ran.append(1) or True],lambda _:(True,()))
  self.assertFalse(r.accepted); self.assertEqual(ran,[])
 def test_drift_invalidates(self):
  s=self.spec(); r=VectorQualifier(self.p).qualify(s,[lambda _:True],lambda _:(True,({"physical":"pass"},))); self.assertTrue(qualification_is_current(r,s)); self.assertFalse(qualification_is_current(r,replace(s,environment={**s.environment,"wirepod":"changed"}))); self.assertFalse(qualification_is_current(r,replace(s,source="changed")))
if __name__=="__main__": unittest.main()
