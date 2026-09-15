# M4 candidate evidence — complete retained archive

PR #109 head `2551585f8951d242db92cd4c3e680409b0e4c572`.
Synthetic merge `6c62e64f2b1251f7ac8e43883207fa2a3240554e`.
Both trees: `0299afd8e0caef5cc247317b5ed2d41423f86a14`.

[Run 35010813043](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35010813043),
job 104522006940, passed actual isolated execution and all 12 capability
probes on Ubuntu 22.04 image `20260907.292.1`.
Pytest: **135 cases plus 78 subtests passed, zero skips**.
JUnit has 135 testcase elements, with 213 in its suite aggregate because it
also counts subtests; there are no failure/error/skipped elements.

Artifact 10413437995 is retained here as `artifact.zip`, SHA-256
`181c57c49e94aaca513f8cf16f83dd2924d1cc0ec12f8105fbb6110047ddc7e1`.
The ZIP recovered from the job's bounded byte export matches GitHub's artifact
metadata digest exactly. All six files were extracted and inspected. The
report, source identity and JUnit agree; tracked source was clean.
The GitHub synthetic commit record independently confirms the tested tree.
Installed dependencies are recorded, not an ER1 frozen dependency lock.

This is candidate qualification evidence. The changed protected lifecycle
test has not been independently accepted; ownership and downstream CI remain
blocked. See the [repair handoff](../../../reviews/pr109/2551585f/README.md).
No future RC, runtime soak, blank-VM install, demo acceptance or research
result is claimed. The original unavailable ZIP at `91c9ae67` remains an
explicit historical retention gap; this complete archive qualifies its own
named candidate only.
