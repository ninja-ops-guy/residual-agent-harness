# Protocol-backed F0 canary plan

The executable protocol canaries MUST use the pinned A2A 1.0.3 API.

## F0-1 — incorrect COMPLETED

Use AgentExecutor with the v1.0 request handler/event queue lifecycle. Emit a deliberately incorrect artifact and reach A2A COMPLETED. Consume the real JSON-RPC stream. COMPLETED is retained as protocol evidence only; the separate spike verifier evaluates the candidate and no accepted receipt exists unless that verifier passes.

## F0-2 — incomplete transport

An exception raised inside AgentExecutor is not sufficient evidence of transport loss. The harness must observe an artifact while the task remains non-terminal and then independently interrupt the server-side transport before a terminal task event is observed. Retain the received bytes and protocol events. Recovery must leave the candidate provisional until explicit authoritative verification occurs.

## Streaming constraint

Record the exact Task/status/artifact event sequence. A stream ending before an interrupted or terminal task state is incomplete protocol evidence and never acceptance.

## Control

A correct COMPLETED flow is a control. Even there, receipt issuance belongs to the spike verifier path rather than the remote A2A state.
