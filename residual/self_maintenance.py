"""Evidence-bounded recursive maintenance primitives.

The controller can evaluate candidate generations and declare them ready for an
external publication step. It intentionally has no merge operation and treats
unknown verification as non-acceptance.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping

class SelfMaintenanceError(ValueError): pass
class VerificationState(str,Enum): PASS="pass"; FAIL="fail"; UNKNOWN="unknown"
class CandidateState(str,Enum): REJECTED="rejected"; PR_READY="pr_ready"
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def digest(value): return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()
FORBIDDEN_ACTIONS=frozenset({"git.merge","git.push.main","branch_protection.write","trust_boundary.write","policy_authority.write","self.approve"})

@dataclass(frozen=True)
class MaintenanceContract:
    mission_id:str; base_commit:str; issue_ref:str; objective:str; writable_paths:tuple[str,...]
    allowed_actions:tuple[str,...]=("file.write","git.commit","pull_request.create"); proposer_id:str="candidate-worker"; verifier_ids:tuple[str,...]=("scope-verifier","behavior-verifier"); max_generations:int=100; require_external_merge:bool=True
    def __post_init__(self):
        if not self.mission_id or not self.base_commit or not self.objective: raise SelfMaintenanceError("mission_id, base_commit and objective are required")
        if not self.writable_paths or len(self.writable_paths)!=len(set(self.writable_paths)): raise SelfMaintenanceError("writable_paths must be a unique non-empty tuple")
        if any(not isinstance(p,str) or not p or p.startswith(("/","\\")) or ".." in p.split("/") for p in self.writable_paths): raise SelfMaintenanceError("writable_paths must be normalized repository-relative paths")
        if any(a in FORBIDDEN_ACTIONS for a in self.allowed_actions): raise SelfMaintenanceError("forbidden authority cannot be granted to self-maintenance")
        if len(set(self.verifier_ids))<2 or self.proposer_id in self.verifier_ids: raise SelfMaintenanceError("at least two verifier identities independent from the proposer are required")
        if type(self.max_generations) is not int or self.max_generations<=0: raise SelfMaintenanceError("max_generations must be positive")
        if self.require_external_merge is not True: raise SelfMaintenanceError("self-maintenance must preserve external merge authority")
    @property
    def contract_hash(self): return digest({"mission_id":self.mission_id,"base_commit":self.base_commit,"issue_ref":self.issue_ref,"objective":self.objective,"writable_paths":self.writable_paths,"allowed_actions":self.allowed_actions,"proposer_id":self.proposer_id,"verifier_ids":self.verifier_ids,"max_generations":self.max_generations,"require_external_merge":self.require_external_merge})

@dataclass(frozen=True)
class CandidateProposal:
    generation:int; parent_receipt_hash:str|None; files:Mapping[str,str]; requested_actions:tuple[str,...]=("file.write","git.commit","pull_request.create"); proposer_id:str="candidate-worker"; metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if type(self.generation) is not int or self.generation<=0: raise SelfMaintenanceError("generation must be positive")
        if not isinstance(self.files,Mapping) or not self.files: raise SelfMaintenanceError("candidate must contain at least one file")
        frozen={}
        for path,content in self.files.items():
            if not isinstance(path,str) or not isinstance(content,str): raise SelfMaintenanceError("candidate files must map string paths to UTF-8 text")
            frozen[path]=content
        object.__setattr__(self,"files",MappingProxyType(frozen)); object.__setattr__(self,"metadata",MappingProxyType(dict(self.metadata)))
    @property
    def proposal_hash(self): return digest({"generation":self.generation,"parent_receipt_hash":self.parent_receipt_hash,"files":dict(sorted(self.files.items())),"requested_actions":self.requested_actions,"proposer_id":self.proposer_id,"metadata":dict(self.metadata)})

@dataclass(frozen=True)
class VerificationResult: verifier_id:str; state:VerificationState; reason:str
@dataclass(frozen=True)
class GenerationReceipt:
    mission_id:str; contract_hash:str; generation:int; proposal_hash:str; previous_receipt_hash:str|None; state:CandidateState; verifications:tuple[VerificationResult,...]; rejection_reason:str|None; merge_authorized:bool=False
    @property
    def receipt_hash(self): return digest({"mission_id":self.mission_id,"contract_hash":self.contract_hash,"generation":self.generation,"proposal_hash":self.proposal_hash,"previous_receipt_hash":self.previous_receipt_hash,"state":self.state.value,"verifications":[{"verifier_id":r.verifier_id,"state":r.state.value,"reason":r.reason} for r in self.verifications],"rejection_reason":self.rejection_reason,"merge_authorized":self.merge_authorized})
Verifier=Callable[[CandidateProposal,MaintenanceContract],tuple[VerificationState,str]]

class ProtectedSelfMaintenanceController:
    def __init__(self,contract): self.contract=contract; self._receipts=[]
    @property
    def receipts(self): return tuple(self._receipts)
    @property
    def last_receipt_hash(self): return self._receipts[-1].receipt_hash if self._receipts else None
    def _reject(self,proposal,reason,verifications=()):
        receipt=GenerationReceipt(self.contract.mission_id,self.contract.contract_hash,proposal.generation,proposal.proposal_hash,self.last_receipt_hash,CandidateState.REJECTED,tuple(verifications),reason,False); self._receipts.append(receipt); return receipt
    def evaluate(self,proposal,verifiers):
        c=self.contract
        if proposal.generation>c.max_generations: return self._reject(proposal,"generation_budget_exhausted")
        if proposal.proposer_id!=c.proposer_id: return self._reject(proposal,"unexpected_proposer_identity")
        if proposal.generation!=len(self._receipts)+1: return self._reject(proposal,"non_monotonic_generation")
        if proposal.parent_receipt_hash!=self.last_receipt_hash: return self._reject(proposal,"parent_receipt_mismatch")
        if any(a in FORBIDDEN_ACTIONS or a not in c.allowed_actions for a in proposal.requested_actions): return self._reject(proposal,"authority_escalation_requested")
        if set(proposal.files)-set(c.writable_paths): return self._reject(proposal,"candidate_write_scope_exceeded")
        if set(verifiers)!=set(c.verifier_ids): return self._reject(proposal,"independent_verifier_set_mismatch")
        results=[]
        for verifier_id in c.verifier_ids:
            try:
                state,reason=verifiers[verifier_id](proposal,c); state=VerificationState(state)
                if not isinstance(reason,str): raise TypeError()
            except Exception: state,reason=VerificationState.UNKNOWN,"verifier_error"
            results.append(VerificationResult(verifier_id,state,reason[:1000]))
        if any(r.state!=VerificationState.PASS for r in results): return self._reject(proposal,"verification_not_unanimous_pass",results)
        receipt=GenerationReceipt(c.mission_id,c.contract_hash,proposal.generation,proposal.proposal_hash,self.last_receipt_hash,CandidateState.PR_READY,tuple(results),None,False); self._receipts.append(receipt); return receipt
    def verify_receipt_chain(self):
        previous=None
        for index,receipt in enumerate(self._receipts,start=1):
            if receipt.generation!=index or receipt.contract_hash!=self.contract.contract_hash or receipt.previous_receipt_hash!=previous or receipt.merge_authorized: return False
            previous=receipt.receipt_hash
        return True

def receipt_to_dict(receipt): return {"mission_id":receipt.mission_id,"contract_hash":receipt.contract_hash,"generation":receipt.generation,"proposal_hash":receipt.proposal_hash,"previous_receipt_hash":receipt.previous_receipt_hash,"state":receipt.state.value,"verifications":[{"verifier_id":r.verifier_id,"state":r.state.value,"reason":r.reason} for r in receipt.verifications],"rejection_reason":receipt.rejection_reason,"merge_authorized":receipt.merge_authorized,"receipt_hash":receipt.receipt_hash}
