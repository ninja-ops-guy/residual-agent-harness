from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from common import EXPECTED_OUTPUT_COMMIT, PROMPTS, create_fixture, finalize, verify_candidate  # noqa: E402
from ai_providers.adapters.ollama_adapter import OllamaAdapter  # noqa: E402
from ai_providers.core import ChatRequest, Message, Role  # noqa: E402
from residual.core import strict_json  # noqa: E402
from residual.engines.protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec  # noqa: E402
from residual.factory.eval_driver import EngineBackedEvaluationDriver, FinalizedRun  # noqa: E402
from residual.factory.eval_framework import FrozenWorkload  # noqa: E402

class FB004OllamaEngine:
    capability_class='agent'; locality='local'
    def __init__(self,model:str,version:str,base_url:str,seed:int|None):
        self.model=model; self.name=f'ollama:{model}'; self.version=version; self.seed=seed
        self.adapter=OllamaAdapter(base_url=base_url,timeout=300.0)
    def supports(self,capability:str)->bool: return capability=='agent'
    def health(self)->EngineHealth: return EngineHealth.HEALTHY
    def normalize(self,raw_output)->EngineResult: return raw_output if isinstance(raw_output,EngineResult) else EngineResult(candidate=raw_output)
    def execute(self,task:TaskSpec,context:ContextAssembly)->EngineResult:
        prompt=PROMPTS.get(task.task_id)
        if prompt is None: raise ValueError('unknown FB004 task')
        deps=context.values.get('dependencies',{})
        note='\nVerified dependency interfaces are already fixed; preserve those contracts.' if deps else ''
        request=ChatRequest(model=self.model,messages=(Message(Role.SYSTEM,'You are completing one bounded file in the FB004 TaskFlow project. Return only JSON matching the schema. No markdown fences.'),Message(Role.USER,prompt+note)),temperature=0,max_tokens=1400,seed=self.seed,response_schema={'type':'object','properties':{'content':{'type':'string'}},'required':['content'],'additionalProperties':False})
        response=self.adapter.chat(request); payload=strict_json(response.content)
        if not isinstance(payload,dict) or set(payload)!={'content'} or not isinstance(payload['content'],str): raise ValueError('FB004 model output violated schema')
        usage=response.usage.get('total_tokens')
        if type(usage) is not int: raise ValueError('Ollama did not report token usage')
        raw=response.raw if isinstance(response.raw,dict) else {}
        return EngineResult(candidate=payload['content'],token_usage=usage,wall_clock_ms=int((raw.get('total_duration') or 0)/1_000_000),raw_metadata={'provenance':'measured','provider':'ollama','model':response.model,'prompt_tokens':response.usage.get('prompt_tokens'),'completion_tokens':response.usage.get('completion_tokens'),'gpu_time_ms':float(raw.get('eval_duration') or 0)/1_000_000})

def main()->int:
    p=argparse.ArgumentParser(description='Execute one measured FB004 configuration/run against Ollama')
    p.add_argument('--config',choices=('single','fixed','dynamic'),required=True); p.add_argument('--run',type=int,required=True)
    p.add_argument('--workload',required=True); p.add_argument('--output',required=True); p.add_argument('--model',required=True); p.add_argument('--model-version',required=True); p.add_argument('--base-url',default='http://localhost:11434')
    args=p.parse_args(); workload=FrozenWorkload.from_dict(strict_json(Path(args.workload).read_text(encoding='utf-8')))
    engine=FB004OllamaEngine(args.model,args.model_version,args.base_url,workload.seed)
    if (engine.name,engine.version)!=(workload.engine_name,workload.engine_version): raise SystemExit('frozen model identity does not match runner')
    with tempfile.TemporaryDirectory(prefix=f'residual-fb004-{args.config}-{args.run}-') as td:
        repo=Path(td)/'repo'; input_commit,_=create_fixture(repo,known_good=False)
        if input_commit!=workload.input_commit: raise SystemExit('fixture input commit does not match frozen workload')
        def verifier(task_id:str,_acceptance:tuple[str,...],candidate)->bool: return isinstance(candidate,str) and verify_candidate(task_id,candidate)
        def finalizer(_workload,outputs,_config,_run_index)->FinalizedRun:
            commit,passed,total=finalize(repo,dict(outputs))
            if commit!=EXPECTED_OUTPUT_COMMIT or commit!=_workload.expected_output_commit: raise ValueError('FB004 final output commit drift')
            return FinalizedRun(commit,passed,total,0)
        driver=EngineBackedEvaluationDriver(engine,finalizer=finalizer,verifier=verifier,fixed_workers=4,max_workers=8)
        measurement=driver.run(workload,args.config,args.run,lambda _event:None)
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(measurement.to_dict(),indent=2,sort_keys=True)+'\n',encoding='utf-8'); return 0

if __name__=='__main__': raise SystemExit(main())
