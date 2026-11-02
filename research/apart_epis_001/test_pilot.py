import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
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
        r=pilot.analyze(self.responses,self.schedule,self.truth,presentation_root=self.root)
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
        result=pilot.analyze(rs,self.schedule,self.truth,presentation_root=self.root)
        for a in result['arms'].values():
            self.assertEqual(a['brier'],0); self.assertEqual(a['incorrect_acceptance_rate'],0)
            self.assertEqual(a['appropriate_hold_rate'],1)

    def test_missing_and_aborted_remain_visible(self):
        rs=copy.deepcopy(self.responses[:-1]); rs[0]['status']='aborted'
        for k in ('decision','acceptance_probability','active_seconds','burden'): rs[0][k]=None
        a=pilot.analyze(rs,self.schedule,self.truth,presentation_root=self.root)['arms']
        self.assertEqual(sum(x['missing'] for x in a.values()),1)
        self.assertEqual(sum(x['aborted'] for x in a.values()),1)
        empty=pilot.analyze([],self.schedule,self.truth,presentation_root=self.root)['arms']
        self.assertTrue(all(x['brier'] is None for x in empty.values()))

    def test_sensitivity_adapter_missing_aborted_and_absent_participant(self):
        rs=copy.deepcopy(self.responses)
        unknown_keys={s['presentation_id'] for s in self.schedule if s['participant_id']=='SYN-001'}
        rs=[r for r in rs if r['presentation_id'] not in unknown_keys]
        rs[0]['status']='aborted'
        for k in ('decision','acceptance_probability','active_seconds','burden'): rs[0][k]=None
        unknown_keys.add(rs[0]['presentation_id'])
        result=pilot.analyze(rs,self.schedule,self.truth,presentation_root=self.root)['uncertainty']
        self.assertEqual(result['participant_counts'],dict.fromkeys('1234',1))
        self.assertIsNone(result['intervals'])
        for a in 'ABCD':
            eligible=[s for s in self.schedule if s['condition']==a and not self.truth[s['case_id']]['acceptance_warranted']]
            missing=sum(s['presentation_id'] in unknown_keys for s in eligible)
            bound=result['sensitivity'][a]['incorrect_acceptance']
            self.assertEqual(bound['assigned_eligible'],11)
            self.assertEqual(bound['unknown'],missing)
            self.assertEqual(bound['lower'],(11-missing)/11)
            self.assertEqual(bound['upper'],1)

    def test_invalid_inputs_fail_closed(self):
        for field,value in [('synthetic',False),('acceptance_probability',float('nan')),
                            ('acceptance_probability',True),('active_seconds',-1),('burden',8),
                            ('decision','PASS'),('presentation_hash','wrong')]:
            rs=copy.deepcopy(self.responses);rs[0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                pilot.analyze(rs,self.schedule,self.truth,presentation_root=self.root)
        with self.assertRaises(ValueError): pilot.analyze(self.responses+self.responses[:1],self.schedule,self.truth,presentation_root=self.root)
        t=copy.deepcopy(self.truth);t[self.schedule[0]['case_id']]['case_hash']='wrong'
        with self.assertRaises(ValueError): pilot.analyze(self.responses,self.schedule,t,presentation_root=self.root)

    def test_reproduction_and_no_overwrite(self):
        other=Path(self.tmp.name)/'again';pilot.build(other)
        for path in self.root.rglob('*'):
            if path.is_file(): self.assertEqual(path.read_bytes(),(other/path.relative_to(self.root)).read_bytes())
        with self.assertRaises(FileExistsError): pilot.build(self.root)
        self.assertEqual(pilot.analyze(self.responses,self.schedule,self.truth,presentation_root=self.root),pilot.analyze(self.responses,self.schedule,self.truth,presentation_root=self.root))

    def test_modified_html_rejected_even_without_responses(self):
        page = self.root/'operator/packet-1/01.html'
        page.write_bytes(page.read_bytes() + b'<!-- changed -->')
        for responses in (self.responses, []):
            with self.assertRaisesRegex(ValueError, 'presentation bytes mismatch'):
                pilot.analyze(responses,self.schedule,self.truth,presentation_root=self.root)

    def test_swapped_html_rejected(self):
        a = self.root/'operator/packet-1/01.html'
        b = self.root/'operator/packet-2/01.html'
        original = a.read_bytes()
        a.write_bytes(b.read_bytes()); b.write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'presentation bytes mismatch'):
            pilot.analyze(self.responses,self.schedule,self.truth,presentation_root=self.root)

    def test_missing_and_symlinked_html_rejected(self):
        page = self.root/'operator/packet-1/01.html'
        saved = self.root/'saved.html'; saved.write_bytes(page.read_bytes())
        page.unlink()
        with self.assertRaisesRegex(ValueError, 'presentation unavailable'):
            pilot.analyze(self.responses,self.schedule,self.truth,presentation_root=self.root)
        page.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, 'symlink forbidden'):
            pilot.analyze(self.responses,self.schedule,self.truth,presentation_root=self.root)

    def test_verified_receipt_and_response_binding(self):
        result = pilot.analyze(self.responses,self.schedule,self.truth,presentation_root=self.root)
        receipt = result['presentation_verification']
        self.assertEqual(receipt['assignment_sha256'],pilot.digest(self.schedule))
        self.assertEqual(len(receipt['presentations']),56)
        for entry, response in zip(receipt['presentations'],self.responses):
            self.assertEqual(set(entry), {'presentation_id','path','sha256'})
            self.assertEqual(entry['sha256'],response['presentation_hash'])
            self.assertEqual(entry['presentation_id'],response['presentation_id'])
        responses=copy.deepcopy(self.responses)
        responses[0]['presentation_hash']=responses[1]['presentation_hash']
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            pilot.analyze(responses,self.schedule,self.truth,presentation_root=self.root)
        with self.assertRaises(TypeError):
            pilot.analyze(self.responses,self.schedule,self.truth)

    def test_cli_rejects_altered_and_swapped_html(self):
        a = self.root/'operator/packet-1/01.html'
        b = self.root/'operator/packet-2/01.html'
        original_a, original_b = a.read_bytes(), b.read_bytes()
        for mode in ('modify','swap'):
            a.write_bytes(original_a + b'changed' if mode=='modify' else original_b)
            b.write_bytes(original_b if mode=='modify' else original_a)
            result = subprocess.run([sys.executable,pilot.__file__,'analyze',str(self.root)],
                                    capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('presentation bytes mismatch',result.stderr)
            self.assertFalse((self.root/'synthetic-analysis.json').exists())

    def test_wrong_verifier_is_not_truth(self):
        byfault={self.truth[c['case_id']]['fault']:c for c in self.cases}
        c=byfault['verifier_false_pass']; self.assertEqual(c['verifier']['verdict'],'PASS')
        self.assertEqual(self.truth[c['case_id']]['decision'],'REJECT')
        c=byfault['verifier_false_fail']; self.assertEqual(c['verifier']['verdict'],'FAIL')
        self.assertEqual(self.truth[c['case_id']]['decision'],'ACCEPT')

if __name__=='__main__': unittest.main()
