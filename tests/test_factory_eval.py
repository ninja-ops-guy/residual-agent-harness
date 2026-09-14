from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from residual.factory.eval_framework import EvaluationError, EvaluationFramework, EvaluationObservationLog, FrozenEvalTask, FrozenWorkload, RunMeasurement, mann_whitney_u
from residual.factory.evidence_bus import StationIdentity

class Driver:
    def __init__(self, simulation=False): self.simulation=simulation
    def run(self,w,c,i,observe):
        scale={"single":10.0,"fixed":4.0,"dynamic":3.0}[c]; observe({"event":"driver","config":c,"run_index":i})
        return RunMeasurement(c,i,scale+i/10,3,100+i,scale/2,0 if c=="single" else .5,1 if c=="single" else 0,0,1,10,10,10,1.0,.5,.25,w.engine_name,w.engine_version,w.expected_output_commit,f"{i:064x}"[-64:],self.simulation)

def workload():
    return FrozenWorkload("w1",("R1","R2","R3"),(
        FrozenEvalTask("t1",("R1",),(),("c1",)),
        FrozenEvalTask("t2",("R2",),("t1",),("c2",)),
        FrozenEvalTask("t3",("R3",),("t1",),("c3",)),
    ),"a"*40,"b"*40,"engine","v1",0.0,7)

class EvalTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.identity=StationIdentity.generate()
    def tearDown(self): self.tmp.cleanup()
    def test_workload_hash_and_cycle(self):
        self.assertEqual(len(workload().workload_hash),64)
        with self.assertRaises(EvaluationError): FrozenWorkload("x",("R",),(FrozenEvalTask("t",("R",),("t",),("c",)),),"a"*40,"b"*40,"e","v",0,1)
    def test_requires_three_runs(self):
        with self.assertRaises(EvaluationError): EvaluationFramework(self.identity,EvaluationObservationLog(self.root/"o")).evaluate(workload(),("single",),2,Driver())
    def test_signed_report_statistics_and_speedup(self):
        log=EvaluationObservationLog(self.root/"o"); r=EvaluationFramework(self.identity,log).evaluate(workload(),("single","fixed","dynamic"),3,Driver())
        self.assertTrue(r.verify(self.identity.public_bytes())); self.assertFalse(r.simulation); self.assertGreater(r.configurations["dynamic"]["speedup_vs_single"],3); self.assertIn("single_vs_dynamic",r.significance)
    def test_simulation_explicit(self):
        r=EvaluationFramework(self.identity,EvaluationObservationLog(self.root/"o")).evaluate(workload(),("single","fixed","dynamic"),3,Driver(True)); self.assertTrue(r.simulation)
    def test_engine_drift_rejected(self):
        class Bad(Driver):
            def run(self,*a,**k):
                m=super().run(*a,**k); d={n:getattr(m,n) for n in m.__dataclass_fields__}; d["engine_version"]="other"; return RunMeasurement(**d)
        with self.assertRaises(EvaluationError): EvaluationFramework(self.identity,EvaluationObservationLog(self.root/"o")).evaluate(workload(),("single",),3,Bad())
    def test_output_drift_rejected(self):
        class Bad(Driver):
            def run(self,*a,**k):
                m=super().run(*a,**k); d={n:getattr(m,n) for n in m.__dataclass_fields__}; d["output_commit"]="c"*40; return RunMeasurement(**d)
        with self.assertRaises(EvaluationError): EvaluationFramework(self.identity,EvaluationObservationLog(self.root/"o")).evaluate(workload(),("single",),3,Bad())
    def test_observation_tamper_detected(self):
        p=self.root/"o"; log=EvaluationObservationLog(p); log.emit({"event":"x"}); row=json.loads(p.read_text().splitlines()[0]); row["event"]="y"; p.write_text(json.dumps(row)+"\n")
        with self.assertRaises(EvaluationError): EvaluationObservationLog(p)
    def test_mann_whitney(self):
        x=mann_whitney_u([1,2,3],[10,11,12]); self.assertLessEqual(x["p_value"],.1); self.assertIn("mann-whitney",x["method"])
    def test_metric_validation(self):
        m=Driver().run(workload(),"single",1,lambda e:None); self.assertEqual(m.metrics()["final_test_pass_rate_pct"],100)
        d={n:getattr(m,n) for n in m.__dataclass_fields__}; d["coordination_time_minutes"]=999
        with self.assertRaises(EvaluationError): RunMeasurement(**d)
if __name__=="__main__": unittest.main()
