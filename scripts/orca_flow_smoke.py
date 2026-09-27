"""Credential-free smoke test for the staged flow runtime."""
from residual.core import ContractError
from residual.orchestrator import Intent, Orchestrator, StageDoor


def main() -> int:
    flow = Orchestrator().flow(Intent("build a calculator safely"))
    ids = [stage.stage_id for stage in flow.stages]
    assert ids[0] == "prepare"
    assert "verify" in ids
    assert ids[-1] == "integrate"
    assert ids.index("verify") < ids.index("integrate")

    try:
        StageDoor.authorize(flow.stage("verify"), write=True)
    except ContractError:
        pass
    else:
        raise AssertionError("verify stage unexpectedly authorized workspace write")

    print(f"flow_hash={flow.flow_hash}")
    print(f"profile={flow.profile.value}")
    print("orca-derived-flow-smoke=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
