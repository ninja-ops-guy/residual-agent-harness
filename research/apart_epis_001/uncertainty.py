"""Synthetic-only statistical kernels; no human ingestion or unblinding API."""
import math
import random

ARMS = 'ABCD'
METRICS = ('incorrect_acceptance', 'appropriate_hold', 'false_rejection', 'brier')
CONTRASTS = (('C', 'B'), ('D', 'C'), ('C', 'A'), ('D', 'A'))


def bounds(values):
    """Sharp [0,1]-outcome bounds over assigned eligible trials; None is unknown."""
    if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v)
                              or not 0 <= v <= 1) for v in values):
        raise ValueError('expected bounded outcomes or None')
    n = len(values)
    observed = [v for v in values if v is not None]
    total = sum(observed)
    return dict(assigned_eligible=n, observed=len(observed), unknown=n-len(observed),
                lower=total/n if n else None,
                upper=(total+n-len(observed))/n if n else None)


def percentile(values, q):
    """Linear interpolation at (n-1)*q, explicitly fixed for reproducibility."""
    ordered = sorted(values)
    index = (len(ordered)-1)*q
    lo = math.floor(index)
    hi = math.ceil(index)
    return ordered[lo] + (ordered[hi]-ordered[lo])*(index-lo)


def summarize(clusters, *, seed=510, resamples=10000):
    """Resample whole synthetic participants within packets, retaining null trials.

    Each cluster has id, packet (1..4), synthetic=True and outcomes[arm][metric].
    Lists contain eligible assigned trial outcomes (None for missing/aborted).
    A packet's assignment shape must match across participants. This kernel
    does not validate presentation bytes; pilot.analyze does that before entry.
    """
    if type(seed) is not int or type(resamples) is not int or resamples < 1:
        raise ValueError('integer seed and positive resamples required')
    strata = {p: [] for p in range(1, 5)}
    ids, shapes = set(), {}
    for c in clusters:
        if (set(c) != {'id', 'packet', 'synthetic', 'outcomes'} or c['synthetic'] is not True
                or not isinstance(c['id'], str) or not c['id'].startswith('SYN-')
                or c['id'] in ids or type(c['packet']) is not int or c['packet'] not in strata):
            raise ValueError('unique synthetic participant and valid packet required')
        ids.add(c['id'])
        if set(c['outcomes']) != set(ARMS):
            raise ValueError('all assigned arms required, including empty outcomes')
        shape = []
        for a in ARMS:
            if set(c['outcomes'][a]) != set(METRICS):
                raise ValueError('all metrics required')
            for m in METRICS:
                v = c['outcomes'][a][m]
                if not isinstance(v, list): raise ValueError('outcome list required')
                bounds(v)
                shape.append(len(v))
        packet = c['packet']
        if packet in shapes and shapes[packet] != shape:
            raise ValueError('incomplete assignment packet; retain unknown outcomes as None')
        shapes[packet] = shape
        strata[packet].append(c)
    for group in strata.values(): group.sort(key=lambda c: c['id'])

    def values(sample, a, m):
        return [v for c in sample for v in c['outcomes'][a][m]]

    sensitivity = {a: {m: bounds(values(clusters, a, m)) for m in METRICS} for a in ARMS}
    differences = {}
    for a, b in CONTRASTS:
        differences[a+'-'+b] = {}
        for m in METRICS:
            x, y = sensitivity[a][m], sensitivity[b][m]
            differences[a+'-'+b][m] = dict(
                lower=None if x['lower'] is None or y['upper'] is None else x['lower']-y['upper'],
                upper=None if x['upper'] is None or y['lower'] is None else x['upper']-y['lower'])
    result = dict(label='SYNTHETIC SOFTWARE VERIFICATION ONLY; NOT HUMAN INFERENCE',
                  sensitivity=sensitivity, sensitivity_differences=differences,
                  seed=seed, requested_resamples=resamples, confidence_level=0.95,
                  method='packet-stratified participant bootstrap; percentile linear interpolation',
                  participant_counts={str(p): len(s) for p, s in strata.items()})
    # One cluster provides no within-stratum variance; never report a fake tight CI.
    if any(len(s) < 2 for s in strata.values()):
        result.update(status='unavailable: fewer than two participants in a packet', intervals=None)
        return result
    draws = {a: {m: [] for m in METRICS} for a in ARMS}
    contrasts = {a+'-'+b: {m: [] for m in METRICS} for a, b in CONTRASTS}
    rng = random.Random(seed)
    for _ in range(resamples):
        sample = [rng.choice(strata[p]) for p in range(1,5) for _ in strata[p]]
        means = {}
        for a in ARMS:
            means[a] = {}
            for m in METRICS:
                observed = [v for v in values(sample,a,m) if v is not None]
                mean = sum(observed)/len(observed) if observed else None
                means[a][m] = mean
                if mean is not None: draws[a][m].append(mean)
        for a,b in CONTRASTS:
            for m in METRICS:
                x,y = means[a][m],means[b][m]
                if x is not None and y is not None: contrasts[a+'-'+b][m].append(x-y)

    def interval(v):
        # Do not silently condition on bootstrap draws with nonempty denominators.
        valid = len(v)
        return dict(valid_resamples=valid, undefined_resamples=resamples-valid,
                    lower=percentile(v,.025) if valid == resamples else None,
                    upper=percentile(v,.975) if valid == resamples else None)
    result.update(status='software fixture only',
                  intervals={a:{m:interval(v) for m,v in ms.items()} for a,ms in draws.items()},
                  contrast_intervals={a:{m:interval(v) for m,v in ms.items()} for a,ms in contrasts.items()})
    return result
