import pytest
from residual.self_maintenance import CandidateProposal,CandidateState,MaintenanceContract,ProtectedSelfMaintenanceController,SelfMaintenanceError,VerificationState

def contract(**changes):
    values=dict(mission_id="selfhost-1",base_commit="0123456789abcdef",issue_ref="#35",objective="repair evidence reproducibility",writable_paths=("a.py","docs.md"),verifier_ids=("scope","behavior"),proposer_id="worker",max_generations=4); values.update(changes); return MaintenanceContract(**values)
def passers(): return {"scope":lambda p,c:(VerificationState.PASS,"scope_ok"),"behavior":lambda p,c:(VerificationState.PASS,"behavior_ok")}
def proposal(controller,generation=1,**changes):
    values=dict(generation=generation,parent_receipt_hash=controller.last_receipt_hash,files={"a.py":"x=1\n"},requested_actions=("file.write","git.commit","pull_request.create"),proposer_id="worker"); values.update(changes); return CandidateProposal(**values)
def test_candidate_can_be_pr_ready_but_never_merge_authorized():
    c=ProtectedSelfMaintenanceController(contract()); result=c.evaluate(proposal(c),passers()); assert result.state==CandidateState.PR_READY; assert result.merge_authorized is False; assert c.verify_receipt_chain()
def test_authority_escalation_and_write_escape_rejected_before_verification():
    for change in ({"requested_actions":("file.write","git.merge")},{"files":{"../main":"bad"}},{"files":{"residual/control_plane/policy.py":"bad"}}):
        c=ProtectedSelfMaintenanceController(contract()); called=[]; verifiers={k:(lambda p,c,k=k:(called.append(k),(VerificationState.PASS,"ok"))[1]) for k in passers()}; result=c.evaluate(proposal(c,**change),verifiers); assert result.state==CandidateState.REJECTED; assert called==[]
def test_unknown_fail_exception_and_missing_independence_do_not_accept():
    cases=[{"scope":lambda p,c:(VerificationState.UNKNOWN,"missing evidence"),"behavior":passers()["behavior"]},{"scope":lambda p,c:(VerificationState.FAIL,"wrong"),"behavior":passers()["behavior"]},{"scope":lambda p,c:(_ for _ in ()).throw(RuntimeError("boom")),"behavior":passers()["behavior"]},{"scope":passers()["scope"]}]
    for verifiers in cases:
        c=ProtectedSelfMaintenanceController(contract()); result=c.evaluate(proposal(c),verifiers); assert result.state==CandidateState.REJECTED; assert result.merge_authorized is False
def test_lineage_requires_exact_parent_and_monotonic_generation():
    c=ProtectedSelfMaintenanceController(contract()); first=c.evaluate(proposal(c),passers()); assert first.state==CandidateState.PR_READY; wrong=CandidateProposal(2,"0"*64,{"a.py":"x=2\n"},proposer_id="worker"); second=c.evaluate(wrong,passers()); assert second.state==CandidateState.REJECTED; assert c.verify_receipt_chain()
def test_contract_cannot_grant_merge_or_use_proposer_as_verifier():
    with pytest.raises(SelfMaintenanceError): contract(allowed_actions=("file.write","git.merge"))
    with pytest.raises(SelfMaintenanceError): contract(verifier_ids=("worker","behavior"))
    with pytest.raises(SelfMaintenanceError): contract(require_external_merge=False)
