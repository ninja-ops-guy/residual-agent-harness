# FAQ

## Why is my task stuck in quarantine?
Inspect the policy reason and pending HITL challenge. Residual will not accept an engine/framework's own approval as authority.

## How do I add a new model provider?
Use `ai_providers/` for model/provider transport. Use `residual.engines` when integrating an agent framework/runtime.

## How do I debug a brake trip?
Inspect `brake_name`, `trip_reason`, and the triggering observation hash in lifecycle/observation events. Do not disable the brake until the triggering condition is understood.

## How do I escalate to a human?
Allow the LoopController to finish as `ESCALATED`; the host HITL module creates the review challenge from that terminal result. Framework-native HITL must remain disabled.
