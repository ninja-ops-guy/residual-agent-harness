import copy
import itertools
import unittest
import uncertainty as u


def fixture():
    """16 invented participants; perfectly dependent judgments within each person."""
    return [dict(id=f'SYN-{p}-{i}', packet=p, synthetic=True,
                 outcomes={a:{m:[float(i % 2)]*3 for m in u.METRICS} for a in u.ARMS})
            for p in range(1,5) for i in range(4)]


class UncertaintyTests(unittest.TestCase):
    def test_bounds_enumerated_completions(self):
        values = [1,0,None,None]
        actual = u.bounds(values)
        completions = [(1+sum(x))/4 for x in itertools.product((0,1),repeat=2)]
        self.assertEqual((actual['lower'],actual['upper']),(min(completions),max(completions)))
        self.assertEqual(u.bounds([.25,None])['lower'],.125)
        self.assertEqual(u.bounds([.25,None])['upper'],.625)

    def test_empty_and_extreme_missingness(self):
        self.assertIsNone(u.bounds([])['lower'])
        self.assertEqual((u.bounds([None]*100)['lower'],u.bounds([None]*100)['upper']),(0,1))
        self.assertEqual(u.bounds([1]*100)['lower'],1)
        for value in (float('nan'),float('inf'),-1,2,True):
            with self.assertRaises(ValueError): u.bounds([value])

    def test_fixed_seed_order_and_dependence(self):
        result = u.summarize(fixture())
        self.assertEqual(result,u.summarize(list(reversed(fixture()))))
        self.assertEqual(result['participant_counts'],dict.fromkeys('1234',4))
        ci = result['intervals']['A']['incorrect_acceptance']
        # Exact Binomial(16,.5) reference: 2.5%/97.5% quantiles 4/16,12/16.
        # Row-wise resampling 48 dependent judgments would spuriously narrow it.
        self.assertEqual((ci['lower'],ci['upper']),(.25,.75))
        for contrast in result['contrast_intervals'].values():
            for interval in contrast.values():
                self.assertEqual((interval['lower'],interval['upper']),(0,0))
        self.assertEqual(ci['valid_resamples'],10000)

    def test_strata_preserved(self):
        clusters=fixture()
        for c in clusters:
            c['outcomes']={a:{m:[int(c['packet']==1)]*3 for m in u.METRICS} for a in u.ARMS}
        ci=u.summarize(clusters,resamples=100)['intervals']['A']['brier']
        self.assertEqual((ci['lower'],ci['upper']),(.25,.25))

    def test_incomplete_responses_retained_and_undefined_draws(self):
        clusters=fixture()
        for c in clusters:
            c['outcomes']['A']['brier']=[None]*3
        clusters[0]['outcomes']['A']['brier']=[1,None,None]
        r=u.summarize(clusters,resamples=100)
        ci=r['intervals']['A']['brier']
        self.assertGreater(ci['undefined_resamples'],0)
        self.assertIsNone(ci['lower'])
        self.assertEqual(r['sensitivity']['A']['brier']['unknown'],47)
        self.assertAlmostEqual(r['sensitivity']['A']['brier']['lower'],1/48)
        self.assertEqual(r['sensitivity']['A']['brier']['upper'],1)

    def test_all_missing_and_empty_metric(self):
        clusters=fixture()
        for c in clusters:
            for a in u.ARMS:
                c['outcomes'][a]['brier']=[None]*3
                c['outcomes'][a]['appropriate_hold']=[]
        r=u.summarize(clusters,resamples=20)
        self.assertEqual(r['intervals']['A']['brier']['undefined_resamples'],20)
        self.assertIsNone(r['sensitivity']['A']['appropriate_hold']['upper'])
        self.assertEqual(r['sensitivity_differences']['C-B']['brier'],dict(lower=-1,upper=1))

    def test_invalid_or_incomplete_assignment_packets(self):
        for mutate in (lambda c:c[0].update(synthetic=False),
                       lambda c:c[0].update(packet=5),
                       lambda c:c.append(copy.deepcopy(c[0])),
                       lambda c:c[0]['outcomes'].pop('A'),
                       lambda c:c[0]['outcomes']['A']['brier'].pop()):
            clusters=fixture();mutate(clusters)
            with self.assertRaises(ValueError): u.summarize(clusters,resamples=2)
        for kwargs in ({'seed':True},{'resamples':0},{'resamples':1.5}):
            with self.assertRaises(ValueError): u.summarize(fixture(),**kwargs)

    def test_missing_or_singleton_packet_unavailable(self):
        for clusters in ([],fixture()[:4],fixture()[3:]):
            r=u.summarize(clusters,resamples=10)
            self.assertIsNone(r['intervals'])
            self.assertIn('unavailable',r['status'])

    def test_percentile_definition(self):
        self.assertEqual(u.percentile([0,1],.025),.025)
        self.assertEqual(u.percentile([1],.975),1)

if __name__ == '__main__': unittest.main()
