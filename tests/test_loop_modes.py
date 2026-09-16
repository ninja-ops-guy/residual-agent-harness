import unittest
from residual.core import Obligation
from residual.eval.loop_modes import NaiveIterationResult, NaiveLoopRunner

class F:
    def __init__(self): self.calls=[]
    def run_all(self, obligations):
        self.calls.append(tuple(o.id for o in obligations))
        return NaiveIterationResult(worker_reports_done=len(self.calls)>=2)

class NaiveLoopTests(unittest.TestCase):
    def test_naive_baseline_reruns_all_and_trusts_worker_completion(self):
        f=F(); obligations=(Obligation("a","a","x"),Obligation("b","b","x"))
        self.assertTrue(NaiveLoopRunner(f).run(obligations,max_iterations=3))
        self.assertEqual(f.calls,[("a","b"),("a","b")])

if __name__ == "__main__": unittest.main()
