# Agent Merge Rule

For any demo/provider boundary PR, an agent may recommend merge only from fresh exact-head evidence. The agent must not pre-authorize the eventual production claim: post-merge published-origin gates still have to run, and their first result is authoritative.

If a post-merge gate fails, the correct response is a new scoped repair revision and requalification—not reinterpretation of the earlier PR green state.
