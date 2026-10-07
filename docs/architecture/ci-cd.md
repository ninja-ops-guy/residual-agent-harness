# Reference architecture: CI/CD

Use Residual as the verification/control layer around build or deployment agents. CI creates a GoalSpec with bounded budgets, an engine performs candidate changes in isolation, structural/mechanical checks run before any judge check, and quarantine policies gate mutating deploy tools. Export receipts as build artifacts and Prometheus metrics to the operator stack. A failed verifier or brake trip blocks promotion rather than trusting agent completion claims.
