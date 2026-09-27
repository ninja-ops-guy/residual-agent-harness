# Vector verified-learning experiment

Assumes Vector control through Wire-Pod/MCP already exists; this branch does not duplicate transport. Inject the existing MCP client as ToolTransport and freeze real tool names in CapabilityPolicy.

Compare A direct LLM→MCP, B RESIDUAL guarded calls, and C guarded calls plus persistent independently-qualified behaviors. Randomize unseen tasks and repeat fresh sessions. Record task completion, unauthorized calls, human interventions, wall time, tokens, MCP calls, repair iterations, qualification false acceptance, environment-drift regressions, and learned-skill reuse. Retain raw OODA events and confidence intervals.

Generated behaviors cannot promote themselves. Hardware canaries begin with bounded low-energy actions and a human-accessible stop. Qualification binds source plus robot/firmware/Wire-Pod/MCP/SDK environment; drift makes the receipt stale.
