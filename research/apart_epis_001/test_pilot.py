import copy
import json
from pathlib import Path
import tempfile
import unittest
import pilot


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'run'
        self.cases,self.truth,self.schedule,self.responses = pilot.build(self.root)

    def test_all_faults_and_four_matched_views(self):
        self.assertEqual(len(self.cases),14)
        for case in self.cases:
            self.assertEqual(case['case_hash'],pilot.digest({k:v for k,v in case.items() if k!='case_hash'}))
            rows=[s for s in self.schedule if s['case_id']==case['case_id']]
            self.assertEqual({s['condition'] for s in rows},set('ABCD'))
            self.assertEqual({s['case_hash'] for s in rows},{case['case_hash']})
        self.assertEqual(len({s['presentation_id'] for s in self.schedule}),56)

    def test_participant_allowlist_and_html_escape(self):
        case=copy.deepcopy(self.cases[0]); case['worker_report']='<script>bad()</script>'
        for a in 'ABCD':
            v=pilot.render(case,a,'opaque')
            self.assertNotIn('case_id',v); self.assertNotIn('case_hash',v)
            self.assertEqual('evidence_receipt' in v,a in 'CD')
            self.assertEqual('verifier' in v,a=='D')
            self.assertEqual('authority' in v,a=='D')
        for p in (self.root/'operator').rglob('*.html'):
            text=p.read_text()
            for forbidden in ('independent_validation','acceptance_warranted','rationale','case_hash'):
                self.assertNotIn(forbidden,text)
            self.assertNotIn('<script',text)

    def test_hand_computed_null_fixture(self):
        r=pilot.analyze(self.responses,self.schedule,self.truth)
        for a in r['arms'].values():
            self.assertEqual(a['incorrect_acceptance_count'],11)
            self.assertEqual(a['nonacceptable_denominator'],11)
            self.assertEqual(a['appropriate_hold_rate'],0)
            self.assertAlmostEqual(a['brier'],(11*.64+3*.04)/14)
        self.assertEqual(set(r['risk_differences'].values()),{0})

    def test_perfect_oracle_software_fixture(self):
        rs=copy.deepcopy(self.responses)
        for r,s in zip(rs,self.schedule):
            t=self.truth[s['case_id']]
            r['decision']=t['decision']; r['acceptance_probability']=int(t['acceptance_warranted'])
        result=pilot.analyze(rs,self.schedule,self.truth)
        for a in result['arms'].values():
            self.assertEqual(a['brier'],0); self.assertEqual(a['incorrect_acceptance_rate'],0)
            self.assertEqual(a['appropriate_hold_rate'],1)

    def test_missing_and_aborted_remain_visible(self):
        rs=copy.deepcopy(self.responses[:-1]); rs[0]['status']='aborted'
        for k in ('decision','acceptance_probability','active_seconds','burden'): rs[0][k]=None
        a=pilot.analyze(rs,self.schedule,self.truth)['arms']
        self.assertEqual(sum(x['missing'] for x in a.values()),1)
        self.assertEqual(sum(x['aborted'] for x in a.values()),1)
        empty=pilot.analyze([],self.schedule,self.truth)['arms']
        self.assertTrue(all(x['brier'] is None for x in empty.values()))

    def test_invalid_inputs_fail_closed(self):
        for field,value in [('synthetic',False),('acceptance_probability',float('nan')),
                            ('acceptance_probability',True),('active_seconds',-1),('burden',8),
                            ('decision','PASS'),('presentation_hash','wrong')]:
            rs=copy.deepcopy(self.responses);rs[0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                pilot.analyze(rs,self.schedule,self.truth)
        with self.assertRaises(ValueError): pilot.analyze(self.responses+self.responses[:1],self.schedule,self.truth)
        t=copy.deepcopy(self.truth);t[self.schedule[0]['case_id']]['case_hash']='wrong'
        with self.assertRaises(ValueError): pilot.analyze(self.responses,self.schedule,t)

    def test_reproduction_and_no_overwrite(self):
        other=Path(self.tmp.name)/'again';pilot.build(other)
        for path in self.root.rglob('*'):
            if path.is_file(): self.assertEqual(path.read_bytes(),(other/path.relative_to(self.root)).read_bytes())
        with self.assertRaises(FileExistsError): pilot.build(self.root)
        self.assertEqual(pilot.analyze(self.responses,self.schedule,self.truth),pilot.analyze(self.responses,self.schedule,self.truth))

    def test_wrong_verifier_is_not_truth(self):
        byfault={self.truth[c['case_id']]['fault']:c for c in self.cases}
        c=byfault['verifier_false_pass']; self.assertEqual(c['verifier']['verdict'],'PASS')
        self.assertEqual(self.truth[c['case_id']]['decision'],'REJECT')
        c=byfault['verifier_false_fail']; self.assertEqual(c['verifier']['verdict'],'FAIL')
        self.assertEqual(self.truth[c['case_id']]['decision'],'ACCEPT')

if __name__=='__main__': unittest.main()
