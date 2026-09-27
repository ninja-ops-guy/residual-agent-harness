# RESIDUAL automated diagnostic runners

These runners turn recurring hardening/recovery tasks into idempotent, evidence-producing workflows.

They deliberately separate **candidate qualification** from **Codex repair**:

- the exact requested candidate is checked in a detached managed worktree;
- every command writes verbose logs and a receipt under
  `${RESIDUAL_AUTOMATION_ROOT:-~/.local/state/residual-automation}`;
- if an unexpected failure occurs, Codex is invoked in a separate local
  `auto-repair/*` worktree;
- a successful Codex repair does **not** change the exact candidate verdict;
- nothing is pushed, merged, approved, or marked ready automatically.

## Codex selection

By default a failure invokes the normal `codex` profile. To use local OSS Codex:

```bash
export AUTO_CODEX_PROFILE=<your-local-profile>
export AUTO_CODEX_TIMEOUT=1200
```

Set `AUTO_CODEX_ON_FAILURE=0` to retain diagnostics without invoking Codex.

Set `AUTO_CODEX_COMMIT=1` only if you want a successful repair worktree
committed locally. It is still never pushed automatically.

## R4-02 B1

Qualifies the promotion-invariant TAR/TAR.ZST successor and proves the frozen
predecessor remains sensitive to the new regression.

```bash
bash scripts/automation/r4_02_b1.sh
```

Defaults:

- predecessor: `2b75b42cd8cf1a7f13eac64a77d86ddfb619d169`
- successor: `e8894c443936710b86efc85e9cbcc29a5f70840e`

Override with `R4_02_B1_BASE_REF` and `R4_02_B1_TARGET_REF`.

## AUD-1 / F6 helper

Qualifies helper/evidence tooling only. **It cannot execute physical F6.**

```bash
bash scripts/automation/f6_helper.sh
```

Defaults:

- helper: `a2567103c7e634310d696e421692fa1f86624e3b`
- frozen product candidate: `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`

A failure gives Codex an isolated helper repair worktree. Candidate/product
paths remain outside the allowed repair scope.

## Shared Comms recovery

This runner operates a completely separate communications-only Station from the
F6 fixture.

```bash
bash scripts/automation/swarm_comms.sh preflight
bash scripts/automation/swarm_comms.sh station-up
bash scripts/automation/swarm_comms.sh bootstrap
bash scripts/automation/swarm_comms.sh status
```

Defaults:

- SC-MESH candidate: `7783081c858ad9ddf98b2e64e740e1104ae5d08b`
- recovery Station: `127.0.0.1:8770`
- F6 port `8766`: reserved and never touched
- old/legacy port `8765`: also refused

Enroll one advisory agent:

```bash
bash scripts/automation/swarm_comms.sh enroll anvil
```

Run the supervised canary:

```bash
bash scripts/automation/swarm_comms.sh canary anvil anvil anvil @ANVIL
```

The canary proves:

1. non-addressed traffic causes zero model invocation;
2. an addressed request yields exactly one response;
3. restart/replay does not duplicate inference or response;
4. tokens remain in mode-0600 files and are never printed.

Only after that canary should additional agents be enrolled. Continuous
communications can be run one agent at a time with:

```bash
bash scripts/automation/swarm_comms.sh bridge-run anvil anvil anvil @ANVIL
```

The advisory bridge uses only SC-MESH `sync`, `messages`, `message`, and
`ack` operations. It contains no task claim, heartbeat, execution-admission,
provider-admission, or result submission path.

For remote hosts, keep Station loopback-only and use a separately constrained
SSH forward to 8770. Do not reuse the F6 SSH identity or its 8766 permit.

## Exit semantics

- `0`: exact candidate/task passed.
- `10`: exact candidate failed, but an isolated Codex repair now verifies.
- `20`: exact candidate failed and Codex repair failed/was blocked.
- other nonzero values: setup/environmental failure.

Always review the run directory and repair patch before promoting a repair.
