# Reference architecture: incident response

NetOps/SecOps modules register scope-aware quarantine policies, verifiers, and brakes. Async telemetry refreshes device/service state into a cache; synchronous verification reads only fresh cached state and returns UNKNOWN when stale. Remediation engines run behind the execution adapter boundary. High-impact actions enter Residual HITL quarantine, and abort cancels pending network I/O within five seconds.
