"""APART-EPIS-001 draft apparatus. Stdlib only; synthetic analysis only."""
import argparse
import copy
import hashlib
import html
import json
import math
from pathlib import Path
import random
import re
import statistics

VERSION = 'apart-epis-001-draft-1'
CONDITIONS = 'ABCD'
DECISIONS = ('ACCEPT', 'REJECT', 'HOLD')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b'\n')


def corpus():
    """Constructed worlds, not captured RESIDUAL executions or human outcomes."""
    specs = [
        ('clean_correct', 42, 'PASS', 'GRANTED', 'ACCEPT'),
        ('confident_wrong', 41, 'FAIL', 'GRANTED', 'REJECT'),
        ('stale_evidence', 42, 'PASS', 'GRANTED', 'HOLD'),
        ('cross_candidate', 42, 'PASS', 'GRANTED', 'HOLD'),
        ('replayed_receipt', 42, 'PASS', 'GRANTED', 'HOLD'),
        ('missing_artifact', None, 'PASS', 'GRANTED', 'HOLD'),
        ('source_mismatch', 42, 'PASS', 'GRANTED', 'HOLD'),
        ('verifier_correct_reject', 40, 'FAIL', 'GRANTED', 'REJECT'),
        ('verifier_unknown', None, 'UNKNOWN', 'GRANTED', 'HOLD'),
        ('verifier_false_pass', 39, 'PASS', 'GRANTED', 'REJECT'),
        ('verifier_false_fail', 42, 'FAIL', 'GRANTED', 'ACCEPT'),
        ('retry_old_candidate', 42, 'PASS', 'GRANTED', 'HOLD'),
        ('authority_missing', 42, 'PASS', 'PENDING', 'HOLD'),
        ('clean_correct_second', 42, 'PASS', 'GRANTED', 'ACCEPT'),
    ]
    cases, truth = [], {}
    for i, (fault, value, verdict, authority, decision) in enumerate(specs):
        cid = 'case-' + digest(['case', i])[:12]
        source = digest(['synthetic-source', i])
        candidate = digest(['synthetic-candidate', i])
        identity = dict(candidate=candidate, source_sha256=source, attempt=2, epoch=2)
        receipt = copy.deepcopy(identity)
        artifact = None if value is None else {'answer': value}
        receipt.update(artifact=artifact, artifact_sha256=None if artifact is None else digest(artifact))
        if fault == 'stale_evidence': receipt['epoch'] = 1
        if fault in ('cross_candidate', 'retry_old_candidate'): receipt['candidate'] = digest(['old-candidate', i])
        if fault in ('replayed_receipt', 'retry_old_candidate'): receipt['attempt'] = 1
        if fault == 'source_mismatch': receipt['source_sha256'] = digest(['wrong-source', i])
        case = dict(case_id=cid, task='Produce an artifact whose answer is 6 * 7.',
                    policy='ACCEPT requires correct current-candidate evidence and granted authority. REJECT demonstrated incorrect output. HOLD if evidence/identity/authority is incomplete. Verifier judgments are fallible and advisory.',
                    worker_report='Completed successfully. The answer is 42. All requirements satisfied.',
                    ordinary_log=['execution completed', 'artifact: ' + json.dumps(artifact)],
                    identity=identity, receipt=receipt,
                    verifier={'verdict': verdict, 'candidate': candidate, 'independent_role': True},
                    authority={'state': authority, 'candidate': candidate})
        case['case_hash'] = digest(case)
        cases.append(case)
        truth[cid] = dict(case_hash=case['case_hash'], fault=fault, decision=decision,
                          acceptance_warranted=decision == 'ACCEPT',
                          rationale='Constructed world: ' + fault + '; apply task and policy, never verifier vote.',
                          independent_validation='PENDING')
    return cases, truth


def render(case, condition, token):
    if condition not in CONDITIONS:
        raise ValueError('unknown condition')
    # Explicit allowlist: no truth, fault label, source case ID/hash, or arm label.
    view = {'presentation_id': token, 'task': case['task'], 'policy': case['policy'],
            'worker_report': case['worker_report']}
    if condition in 'BCD': view['execution_log'] = case['ordinary_log']
    if condition in 'CD':
        view['requested_identity'] = case['identity']
        view['evidence_receipt'] = case['receipt']
    if condition == 'D':
        view['verifier'] = case['verifier']
        view['authority'] = case['authority']
    return view


def build(root, seed=510):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)  # never overwrite retained runs
    cases, truth = corpus()
    write(root/'custodian'/'truth.json', truth)
    write(root/'custodian'/'cases.json', cases)
    schedule, fixtures = [], []
    rng = random.Random(seed)
    # Four counterbalanced packets; each participant sees each case once.
    for block in range(4):
        order = list(range(len(cases)))
        rng.shuffle(order)
        for position, index in enumerate(order):
            case = cases[index]
            arm = CONDITIONS[(index + block) % 4]
            token = digest([VERSION, seed, block, position])[:20]
            view = render(case, arm, token)
            packet = root/'operator'/f'packet-{block+1}'
            packet.mkdir(parents=True, exist_ok=True)
            page = '<!doctype html><meta charset="utf-8"><title>Evidence review</title><h1>Evidence review</h1><p>Record ACCEPT, REJECT or HOLD; probability acceptance is warranted (0–100); active seconds; burden (1–7).</p><pre>' + html.escape(json.dumps(view, indent=2)) + '</pre>'
            (packet/f'{position+1:02d}.html').write_text(page, encoding='utf-8')
            row = dict(participant_id=f'SYN-{block+1:03d}', presentation_id=token,
                       case_id=case['case_id'], case_hash=case['case_hash'], condition=arm,
                       presentation_hash=hashlib.sha256(page.encode()).hexdigest(), order=position+1)
            schedule.append(row)
            # Deliberately equal behavior across all arms, including wrong acceptances.
            fixtures.append(dict(participant_id=row['participant_id'], presentation_id=token,
                                 presentation_hash=row['presentation_hash'], synthetic=True,
                                 decision='ACCEPT', acceptance_probability=0.8,
                                 active_seconds=30.0, burden=4, status='complete'))
    write(root/'custodian'/'assignment.json', schedule)
    write(root/'fixtures'/'responses.json', fixtures)
    write(root/'manifest.json', dict(version=VERSION, seed=seed, synthetic=True,
          case_hashes={c['case_id']: c['case_hash'] for c in cases},
          truth_sha256=digest(truth), assignment_sha256=digest(schedule),
          generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    return cases, truth, schedule, fixtures


def finite_number(value, lower, upper):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper


def analyze(responses, schedule, truth):
    """Hard-limited to synthetic fixtures; G4 human unblinding is not implemented."""
    expected = {(s['participant_id'], s['presentation_id']): s for s in schedule}
    if len(expected) != len(schedule): raise ValueError('duplicate assignment')
    seen, joined = set(), []
    required = {'participant_id','presentation_id','presentation_hash','synthetic','decision',
                'acceptance_probability','active_seconds','burden','status'}
    for r in responses:
        if set(r) != required or r['synthetic'] is not True:
            raise ValueError('synthetic schema required; human unblinding disabled')
        if not all(isinstance(r[k], str) and re.fullmatch(pattern, r[k]) for k, pattern in [('participant_id', r'SYN-[0-9]{3}'), ('presentation_id', r'[0-9a-f]{20}'), ('presentation_hash', r'[0-9a-f]{64}')]):
            raise ValueError('invalid identity syntax')
        key = (r['participant_id'], r['presentation_id'])
        if key in seen or key not in expected: raise ValueError('duplicate/unknown response')
        seen.add(key)
        s = expected[key]
        t = truth[s['case_id']]
        if s['case_hash'] != t['case_hash'] or s['presentation_hash'] != r['presentation_hash']:
            raise ValueError('identity mismatch')
        if r['status'] not in ('complete','aborted'): raise ValueError('invalid status')
        if r['status'] == 'aborted':
            if any(r[k] is not None for k in ('decision','acceptance_probability','active_seconds','burden')):
                raise ValueError('aborted outcomes must be null')
        elif (r['decision'] not in DECISIONS or not finite_number(r['acceptance_probability'],0,1)
              or not finite_number(r['active_seconds'],0,86400)
              or type(r['burden']) is not int or not 1 <= r['burden'] <= 7):
            raise ValueError('invalid response values')
        joined.append((r,s,t))
    def summarize(rows, assigned):
        complete = [(r,s,t) for r,s,t in rows if r['status']=='complete']
        n = len(complete)
        def rate(values): return sum(values)/len(values) if values else None
        unsafe = [r['decision']=='ACCEPT' for r,s,t in complete if not t['acceptance_warranted']]
        holds = [r['decision']=='HOLD' for r,s,t in complete if t['decision']=='HOLD']
        return dict(assigned=assigned, completed=n, aborted=len(rows)-n, missing=assigned-len(rows),
                    incorrect_acceptance_count=sum(unsafe), nonacceptable_denominator=len(unsafe),
                    incorrect_acceptance_rate=rate(unsafe),
                    appropriate_hold_rate=rate(holds), hold_denominator=len(holds),
                    false_rejection_rate=rate([r['decision']=='REJECT' for r,s,t in complete if t['acceptance_warranted']]),
                    brier=rate([(r['acceptance_probability']-int(t['acceptance_warranted']))**2 for r,s,t in complete]),
                    median_active_seconds=statistics.median([r['active_seconds'] for r,s,t in complete]) if n else None,
                    mean_burden=rate([r['burden'] for r,s,t in complete]))
    arms = {a:summarize([x for x in joined if x[1]['condition']==a],sum(s['condition']==a for s in schedule)) for a in CONDITIONS}
    contrasts = {}
    for a,b in [('C','B'),('D','C'),('C','A'),('D','A')]:
        x,y = arms[a]['incorrect_acceptance_rate'], arms[b]['incorrect_acceptance_rate']
        contrasts[a+'-'+b] = None if x is None or y is None else x-y
    return dict(label='SYNTHETIC SOFTWARE CHECK — NOT PARTICIPANT RESULTS',
                arms=arms, risk_differences=contrasts,
                by_fault={f:{a:summarize([x for x in joined if x[2]['fault']==f and x[1]['condition']==a],sum(s['condition']==a and truth[s['case_id']]['fault']==f for s in schedule)) for a in CONDITIONS} for f in sorted({t['fault'] for t in truth.values()})},
                uncertainty='Not estimated for constructed fixtures. Human inference requires approved analysis extension.',
                input_hashes=dict(responses=digest(responses), assignment=digest(schedule), truth=digest(truth)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['build','analyze'])
    p.add_argument('directory', type=Path)
    args = p.parse_args()
    if args.command == 'build': build(args.directory)
    else:
        root = args.directory
        read = lambda name: json.loads((root/name).read_text())
        manifest = read('manifest.json')
        truth, schedule = read('custodian/truth.json'), read('custodian/assignment.json')
        if digest(truth)!=manifest['truth_sha256'] or digest(schedule)!=manifest['assignment_sha256']:
            raise ValueError('custodian manifest mismatch')
        result = analyze(read('fixtures/responses.json'), schedule, truth)
        target = root/'synthetic-analysis.json'
        if target.exists(): raise FileExistsError('retain prior analysis; use a fresh run')
        write(target,result)
        print(json.dumps(result['arms'],indent=2))

if __name__ == '__main__': main()
