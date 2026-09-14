"""Opt-in Ollama receipt-cache benchmark. Never substitutes simulated inference."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import math
from pathlib import Path
import platform
import time

from .core import Artifact, ContractError, Obligation, Registry, Task, canonical, digest, register_builtins
from .engine import Harness, Limits
from .modular import ModularProvider, normalized_usage
from .providers import Reply
from .receipts import StationReceipt, validate_receipt_graph
from .storage import Cache


def benchmark_task(changed=False):
    return Task('receipt-cache-benchmark', 'Compute two bounded values from public synthetic evidence',
        {'source': Artifact('source', canonical({'numbers':[11, 23, 28 if changed else 27], 'label':'alpha'}))}, (
            Obligation('total', 'Return the sum of source.numbers as a JSON number.', 'json_sum', ('source',),
                       parameters={'artifact':'source', 'pointer':'/numbers'}),
            Obligation('label', 'Return source.label as a JSON string; total is a verified prerequisite.',
                       'json_value', ('source',), ('total',), {'artifact':'source','pointer':'/label'})))


def summarize(result, elapsed_ms, task):
    complete = True
    inputs = outputs = 0
    sources = []
    for call in result['calls']:
        usage = call['usage']; sources.append(usage['source'])
        if (usage['source'] != 'reported' or any(type(usage.get(k)) is not int or usage[k] < 0
                for k in ('input_tokens', 'output_tokens'))):
            complete = False
        else:
            inputs += usage['input_tokens']; outputs += usage['output_tokens']
    receipts = {k: StationReceipt.from_dict(v) for k,v in result['station_receipts'].items()}
    valid = bool(result['success'])
    if valid:
        validate_receipt_graph(receipts, {o.id:o.depends_on for o in task.obligations})
        valid = all(r.value_hash == digest(result['values'][k]) for k,r in receipts.items())
    return {'success':valid, 'elapsed_ms':elapsed_ms, 'calls':len(result['calls']),
            'cache_hits':result['metrics']['cache_hits'], 'input_tokens':inputs if complete else None,
            'output_tokens':outputs if complete else None, 'usage_complete':complete, 'usage_sources':sources,
            'values_hash':digest(result['values']), 'receipt_hashes':{k:r.receipt_hash for k,r in receipts.items()}}


def run_trial(provider_factory, index, *, repeats=3, limits=None):
    """Each worker owns its provider, verifier registry and SQLite connection."""
    registry = Registry(); register_builtins(registry)
    provider = provider_factory()
    task = benchmark_task(); changed = benchmark_task(True)
    limits = limits or Limits(local_rounds=3, expert_rounds=0, max_calls=12, max_expert_calls=0)
    cache = Cache()
    def run(current, selected_cache):
        harness = Harness(registry, provider, None, limits=limits, cache=selected_cache, mode='no_solvers')
        start = time.perf_counter()
        result = harness.run(current)
        return summarize(result, (time.perf_counter()-start)*1000, current)
    try:
        seed = run(task, cache)
        pairs = []
        for repetition in range(repeats):
            order = ['cached','uncached'] if (index+repetition)%2 else ['uncached','cached']
            pair = {'order':order}
            for condition in order:
                pair[condition] = run(task, cache if condition == 'cached' else None)
            pair['equivalent'] = pair['cached']['values_hash'] == pair['uncached']['values_hash'] == seed['values_hash']
            pairs.append(pair)
        invalidated = run(changed, cache)
        return {'worker':index, 'seed':seed, 'pairs':pairs, 'changed_evidence':invalidated}
    finally:
        cache.close()


def aggregate(trials):
    cached = [p['cached'] for t in trials for p in t['pairs']]
    uncached = [p['uncached'] for t in trials for p in t['pairs']]
    all_samples = cached + uncached + [s for t in trials for s in (t['seed'],t['changed_evidence'])]
    valid = (bool(trials) and all(s['success'] for s in all_samples)
        and all(p['equivalent'] for t in trials for p in t['pairs'])
        and all(s['cache_hits']==2 and s['calls']==0 for s in cached)
        and all(s['calls']>0 and s['cache_hits']==0 for s in uncached)
        and all(t['seed']['calls']>0 and t['changed_evidence']['calls']>0
                and t['changed_evidence']['cache_hits']==0
                and t['seed']['values_hash'] != t['changed_evidence']['values_hash'] for t in trials))
    complete = all(s['usage_complete'] for s in all_samples)
    def percentiles(samples):
        values = sorted(s['elapsed_ms'] for s in samples)
        return {f'p{q}_ms':values[max(0, math.ceil(q/100*len(values))-1)] if values else None for q in (50,95)}
    def total(samples): return sum(s['input_tokens']+s['output_tokens'] for s in samples)
    return {'validation_passed':valid, 'usage_complete':complete,
        'measured_token_reduction':total(uncached)-total(cached) if valid and complete else None,
        'avoided_calls':sum(s['calls'] for s in uncached)-sum(s['calls'] for s in cached) if valid else None,
        'cached_latency':percentiles(cached), 'uncached_latency':percentiles(uncached),
        'interpretation':'Matched repeat-task cache reuse only; excludes cache-fill cost. Not a general model-efficiency claim.'}


class MeasuredOllamaProvider(ModularProvider):
    def generate(self, packet, max_output_tokens):
        start = time.perf_counter()
        response = self.router.chat(self.kind+':'+self.model, self.request(packet,max_output_tokens))
        if response.model != self.model:
            raise ContractError('provider response model differs from pinned model name')
        return Reply(response.content, normalized_usage(response.usage),
                     (time.perf_counter()-start)*1000, response.finish_reason)


def model_identity(provider, requested):
    # Uses the existing bounded, redirect-rejecting HTTP transport, not a new HTTP client.
    payload = provider.adapter._json(provider.profile['base_url']+'/api/tags')
    names = {requested, requested+':latest'} if ':' not in requested else {requested}
    matches = [m for m in payload['models'] if m.get('name') in names]
    if len(matches) != 1 or not isinstance(matches[0].get('digest'),str) or not matches[0]['digest']:
        raise ContractError('requested local model is not installed or has ambiguous identity')
    return {'name':matches[0]['name'], 'digest':matches[0]['digest']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='llama3.3')
    parser.add_argument('--base-url', default='http://127.0.0.1:11434')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--output', default='runs/live-cache-benchmark.json')
    args = parser.parse_args(argv)
    if not (1<=args.repeats<=50 and 1<=args.concurrency<=8 and math.isfinite(args.timeout) and 1<=args.timeout<=300):
        parser.error('repeats 1..50, concurrency 1..8, timeout 1..300 seconds required')
    report = {'schema_version':'residual.live.cache.benchmark.v1', 'status':'blocked',
        'model_requested':args.model, 'live_model_validated':False, 'token_savings':None,
        'configuration':{'repeats':args.repeats,'concurrency':args.concurrency,'timeout_s':args.timeout},
        'python':platform.python_version(), 'platform':platform.system(), 'started_at_ns':time.time_ns(),
        'scope':'Synthetic two-obligation DAG; uncached calls use a warm runtime, not a cold-model-load benchmark.'}
    try:
        profile = {'kind':'ollama','model':args.model,'base_url':args.base_url,'placement':'local'}
        probe = MeasuredOllamaProvider(profile); probe.adapter.timeout=3
        before = model_identity(probe,args.model); report['model_identity']=before
        profile['model'] = before['name']
        def provider_factory():
            provider=MeasuredOllamaProvider(profile); provider.adapter.timeout=args.timeout
            return provider
        limits = Limits(local_rounds=3,expert_rounds=0,max_calls=12,max_expert_calls=0)
        report['limits']=asdict(limits); report['configuration_hash']=digest({**report['configuration'],'limits':asdict(limits)})
        start=time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            trials = list(pool.map(lambda i:run_trial(provider_factory,i,repeats=args.repeats,limits=limits),range(args.concurrency)))
        report['experiment_wall_clock_s']=time.perf_counter()-start
        report['trials']=trials; report['summary']=aggregate(trials)
        stable = model_identity(probe,args.model) == before
        report['model_identity_stable']=stable
        valid=report['summary']['validation_passed'] and report['summary']['usage_complete'] and stable
        report.update(status='passed' if valid else 'inconclusive', live_model_validated=valid,
                      token_savings=report['summary']['measured_token_reduction'] if valid else None)
    except Exception:
        # Provider errors may contain keys, URLs or user paths. Persist fixed diagnostic codes only.
        report['blocker']='ollama_or_model_unavailable' if 'trials' not in report else 'benchmark_validation_failed'
    destination=Path(args.output); destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(canonical(report)+'\n',encoding='utf-8')
    print(canonical({'status':report['status'],'live_model_validated':report['live_model_validated']}))
    return 0 if report['status']=='passed' else 3


if __name__ == '__main__':
    raise SystemExit(main())
