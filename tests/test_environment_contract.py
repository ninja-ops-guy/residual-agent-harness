from __future__ import annotations

import unittest

from residual.environment_contract import (
    EnvironmentContract, EnvironmentRequirement, EnvironmentStatus,
    qualify_environment,
)


class EnvironmentContractTests(unittest.TestCase):
    def setUp(self):
        self.contract=EnvironmentContract({
            "repo_tree":(EnvironmentRequirement.REQUIRED_EXACT,"tree-a"),
            "python":(EnvironmentRequirement.REQUIRED_COMPATIBLE,"3.12"),
            "queue_latency_s":(EnvironmentRequirement.OBSERVATIONAL,None),
        })

    def test_env_required_exact_drift_fails(self):
        verdict=qualify_environment(self.contract,{
            "repo_tree":"tree-b","python":"3.12","queue_latency_s":900,
        })
        self.assertEqual(verdict.status,EnvironmentStatus.FAIL)
        self.assertEqual(verdict.exact_mismatches,("repo_tree",))
        self.assertEqual(verdict.observations["queue_latency_s"],900)

    def test_env_observational_drift_does_not_change_pass(self):
        a=qualify_environment(self.contract,{
            "repo_tree":"tree-a","python":"3.12","queue_latency_s":1,
        })
        b=qualify_environment(self.contract,{
            "repo_tree":"tree-a","python":"3.12","queue_latency_s":9999,
        })
        self.assertEqual(a.status,EnvironmentStatus.PASS)
        self.assertEqual(b.status,EnvironmentStatus.PASS)
        self.assertNotEqual(a.observed_environment_hash,b.observed_environment_hash)

    def test_env_compatible_drift_requires_explicit_verdict(self):
        verdict=qualify_environment(self.contract,{
            "repo_tree":"tree-a","python":"3.13","queue_latency_s":10,
        })
        self.assertEqual(verdict.status,EnvironmentStatus.COMPATIBILITY_REQUIRED)
        self.assertEqual(verdict.compatibility_checks,("python",))


if __name__=="__main__":
    unittest.main()
