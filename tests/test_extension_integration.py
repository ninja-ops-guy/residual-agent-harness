"""Failure-path checks for imported components and real station integration."""
import dataclasses
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from residual import CheckResult, LoopController, Verifier, StationExtensionRegistry, RunOutcome, ProposedAction
from residual.core import ContractError, digest
from residual.hitl import HITLEscalationGateway, HITLStatus
from residual.memory import EpistemicMemoryStore
from residual.mesh import MeshIdentity, MeshNode, MeshMessageKind
from residual.modules.adapters import HITLModule, MeshModule, MemoryModule
from residual.modules.netops import NetOpsModule
from residual.modules.secops import SecOpsModule
from residual.trajectory import TrajectoryRecorder, TrajectoryStep, TrajectoryRegressionEngine
from residual.station.service import Station, DEMO_FILES, demo_spec
from residual.station.extensions import validate_task_receipt
from tests.test_foundation import spec, Sample, Pass, identity
from tests import test_foundation as foundation


class ImportedIntegrityTests(unittest.TestCase):
    def test_trajectory_hash_and_fingerprint_checks(self):
        with tempfile.TemporaryDirectory() as d:
            recorder=TrajectoryRecorder(d)
            first=recorder.record('goal',[TrajectoryStep(1,'read','a','pass',10)],[],'success')
            same=recorder.record('goal',[TrajectoryStep(1,'read','a','pass',99)],[],'success')
            self.assertEqual(first.trajectory_hash,same.trajectory_hash)
            different=recorder.record('goal',[TrajectoryStep(1,'read','b','pass')],[],'success')
            self.assertFalse(TrajectoryRegressionEngine(recorder).evaluate_regression(different,first.trajectory_hash)[0])
            Path(d,first.trajectory_hash+'.json').write_text('{}')
            self.assertIsNone(recorder.load(first.trajectory_hash))
            with self.assertRaises(ContractError):recorder.load('../outside')

    def test_memory_needs_current_revision_and_live_verification(self):
        receipt=foundation.ReceiptTests().receipt()
        with tempfile.TemporaryDirectory() as d:
            memory=EpistemicMemoryStore(d)
            entry=memory.index('goal',receipt.receipt_hash,{'receipt':receipt.to_dict(),'value':True},receipt.verifier_revision)
            self.assertEqual(len(entry.key),64)
            self.assertIsNone(memory.retrieve_verified('goal',verifier_revision=digest('stale'),verify=lambda r,v:True))
            self.assertIsNone(memory.retrieve_verified('goal',verifier_revision=receipt.verifier_revision,verify=lambda r,v:False))
            self.assertIsNotNone(memory.retrieve_verified('goal',verifier_revision=receipt.verifier_revision,verify=lambda r,v:v is True))
            data=json.loads(Path(d,entry.key+'.json').read_text());data['artifact_payload']['value']=False
            Path(d,entry.key+'.json').write_text(json.dumps(data))
            self.assertIsNone(memory.retrieve('goal'))

    def test_challenge_signature_is_not_operator_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            gateway=HITLEscalationGateway(b'k'*32,d)
            challenge=gateway.generate_challenge('task',{},'review',spec())
            self.assertEqual(gateway.verify_approval(challenge.challenge_id,challenge.signature,'operator',('operator',)),HITLStatus.DENIED)

    def test_hitl_atomic_single_use_across_instances(self):
        with tempfile.TemporaryDirectory() as d:
            auth=lambda c,response,role: response == 'host-authenticated-token'
            gateway=HITLEscalationGateway(b'k'*32,d,authenticate=auth)
            challenge=gateway.generate_challenge('task',{},'review',spec())
            gateways=[HITLEscalationGateway(b'k'*32,d,authenticate=auth) for _ in range(4)]
            def approve(g):return g.verify_approval(challenge.challenge_id,'host-authenticated-token','operator',('operator',))
            with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(approve,gateways))
            self.assertEqual(results.count(HITLStatus.APPROVED),1)
            self.assertEqual(results.count(HITLStatus.DENIED),3)

    def test_hitl_signed_expiry_role_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            gateway=HITLEscalationGateway(b'k'*32,d,authenticate=lambda *a:True)
            challenge=gateway.generate_challenge('task',{},'review',spec())
            self.assertIsNone(gateway.get_challenge('../outside'))
            self.assertEqual(gateway.verify_approval(challenge.challenge_id,'ok','admin',('admin',)),HITLStatus.DENIED)
            with sqlite3.connect(Path(d,'challenges.sqlite3')) as db:
                raw=db.execute('SELECT record FROM challenges').fetchone()[0]
                data=json.loads(raw);data['validity_window_s']=999999999
                db.execute('UPDATE challenges SET record=?',(json.dumps(data),))
            self.assertIsNone(gateway.get_challenge(challenge.challenge_id))
            self.assertEqual(gateway.verify_approval(challenge.challenge_id,'ok','operator',('operator',)),HITLStatus.DENIED)

    def test_hitl_expired_and_abort_do_not_approve(self):
        with tempfile.TemporaryDirectory() as d:
            gateway=HITLEscalationGateway(b'k'*32,d,authenticate=lambda *a:True)
            challenge=gateway.generate_challenge('task',{},'review',spec())
            with patch('residual.hitl.gateway.time.time_ns',return_value=challenge.timestamp_ns+int(3601e9)):
                self.assertEqual(gateway.verify_approval(challenge.challenge_id,'ok','operator',('operator',)),HITLStatus.EXPIRED)
            hitl=HITLModule(gateway)
            registry=StationExtensionRegistry().register_module(Sample()).register_module(hitl)
            class UnknownUsage(Pass):
                def run_pass(self,*args):return {'candidate':True,'tokens_used':None}
            result=LoopController(spec(),Verifier({}),UnknownUsage(),extensions=registry).run()
            self.assertEqual(result.outcome,RunOutcome.ABORTED);self.assertIsNone(hitl.last)

    def test_hitl_escalation_generates_challenge_via_registry(self):
        with tempfile.TemporaryDirectory() as d:
            hitl=HITLModule(HITLEscalationGateway(b'k'*32,d))
            registry=StationExtensionRegistry().register_module(Sample()).register_module(hitl)
            result=LoopController(spec(max_passes=1),Verifier({}),Pass(False),extensions=registry).run()
            self.assertEqual(result.outcome,RunOutcome.ESCALATED)
            self.assertEqual(hitl.last.goal_spec_hash,result.spec_hash)

    def test_secops_scans_frozen_nested_arrays(self):
        module=SecOpsModule(['PRIVATE KEY'],['MIT'])
        action=ProposedAction('file_write','files',{'items':[{'body':'PRIVATE KEY'}]})
        self.assertIsNotNone(module.quarantine_policies()[0](action))

    def test_netops_samples_zero_window_and_rejects_missing_metrics(self):
        class Telemetry:
            def get_current_metrics(self):return {}
        module=NetOpsModule(Telemetry(),{'loss':1.0})
        result,_=module.verifiers()['telemetry_stabilization'][1]({}, {'evaluation_window_sec':0,'poll_interval_sec':0})
        self.assertEqual(result,CheckResult.UNKNOWN)
        self.assertEqual(module.brakes()[0].update({}).recommended_action.value,'abort')
        action=ProposedAction('config_change','apply',{'target_device':'core','permitted_devices':['core']})
        self.assertIsNotNone(module.quarantine_policies()[1](action))

    def test_netops_host_telemetry_stops_before_worker_dispatch(self):
        class Telemetry:
            def get_current_metrics(self):return {'loss':4.0,'topology_hash':'base'}
        module=NetOpsModule(Telemetry(),{'loss':1.0})
        registry=StationExtensionRegistry().register_module(Sample())
        registry.register_module(module,revisions={name:identity() for name in module.verifiers()})
        worker=Pass(observations=[{'kind':'custom','payload':{'loss':0}}])
        result=LoopController(spec(),Verifier({}),worker,extensions=registry).run()
        self.assertEqual(result.outcome,RunOutcome.ABORTED);self.assertEqual(worker.calls,0)

    def test_mesh_signed_payload_cannot_mutate_and_verifier_exception_denies(self):
        a=MeshIdentity('device-a','A','pk-a',(),'',0)
        b=MeshIdentity('device-b','B','pk-b',(),'',0)
        sign=lambda data:digest(data.decode())
        def verify(pk,data,sig):return sig == sign(data)
        sender=MeshNode(a,sign,verify);receiver=MeshNode(b,sign,verify)
        receiver.connect_peer(a)
        payload={'nested':{'value':1}}
        message=sender.send_message(MeshMessageKind.CHAT,payload=payload)
        payload['nested']['value']=2
        self.assertEqual(message.payload['nested']['value'],1)
        self.assertTrue(receiver.receive_message(message));self.assertFalse(receiver.receive_message(message))
        with self.assertRaises(ContractError):receiver.connect_peer(dataclasses.replace(a,public_key='replacement'))
        bad=MeshNode(b,sign,lambda *a:(_ for _ in ()).throw(RuntimeError()))
        bad.connect_peer(a);self.assertFalse(bad.receive_message(message))

    def test_mesh_module_only_broadcasts_receipt_references_at_close(self):
        node=MeshNode(MeshIdentity('a','A','pk',(),'',0),lambda data:'signature',lambda *a:True)
        receipt=foundation.ReceiptTests().receipt()
        module=MeshModule(node,lambda result:[receipt])
        registry=StationExtensionRegistry().register_module(Sample()).register_module(module)
        LoopController(spec(),Verifier({}),Pass(),extensions=registry).run()
        self.assertEqual(len(node.chat.messages),1)
        payload=node.chat.messages[0].payload
        self.assertEqual(payload['receipt_hash'],receipt.receipt_hash);self.assertEqual(payload['result'],'')


class StationFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.station=Station(self.temp.name);self.pid=self.station.create(demo_spec(),demo=True)['project_id']

    def test_real_batch_receipt_dag_and_artifacts_with_observations_off(self):
        self.station.store.settings({'observations_enabled':False})
        result=self.station.batch(self.pid)
        self.assertEqual(result['integrated'],3)
        project=self.station.store.project(self.pid)
        by_id={t['id']:t for t in project['tasks']}
        child,_=validate_task_receipt(self.station,project,by_id['OPS-103'])
        self.assertEqual({p.task_id for p in child.parent_receipts},{'OPS-101','OPS-102'})
        for task in project['tasks']:
            self.assertTrue(any(a['kind']=='receipt' for a in task['artifacts']))
        self.assertEqual(self.station.extensions(self.pid).diagnostics,())
        events=self.station.store.events(self.pid,0,100000)
        control=[e['data']['control']['event'] for e in events if 'control' in e['data']]
        self.assertEqual(control,['run_opened','run_closed'])
        self.assertTrue(list(Path(self.temp.name,'extensions',self.pid,'trajectories').glob('*.json')))
        self.assertEqual(len(list(Path(self.temp.name,'extensions',self.pid,'memory').glob('*.json'))),3)

    def test_prewrite_policy_blocks_secret_before_git_or_disk_change(self):
        self.station.triage(self.pid)
        work=self.station.prepare(self.pid,'runner','OPS-101')
        target=Path(self.station.store.task(self.pid,'OPS-101')['candidate_dir'],'station/health.py')
        before=target.read_text()
        with self.assertRaisesRegex(ContractError,'extension policy'):
            self.station.finish(work,{'files':{'station/health.py':'-----BEGIN PRIVATE KEY-----'}})
        self.assertEqual(target.read_text(),before)
        self.assertEqual(self.station.store.task(self.pid,'OPS-101')['state'],'repair_required')

    def test_prestaging_sast_blocks_uncommitted_credential_assignment(self):
        self.station.triage(self.pid)
        work=self.station.prepare(self.pid,'runner','OPS-101')
        from residual.station import workspace as ws
        folder=self.station.store.task(self.pid,'OPS-101')['candidate_dir'];head=ws.git(folder,'rev-parse','HEAD')
        with self.assertRaisesRegex(ContractError,'SecOps'):
            self.station.finish(work,{'files':{'station/health.py':'api_key = "real-looking-value"\n'}})
        self.assertEqual(ws.git(folder,'rev-parse','HEAD'),head)
        self.assertEqual(ws.git(folder,'diff','--cached','--name-only'),'')

    def test_stale_receipt_blocks_later_success_and_export(self):
        self.station.batch(self.pid)
        task=self.station.store.task(self.pid,'OPS-101')
        task['verification_receipt']['value']['head_commit']='forged'
        self.station.store.update_task(self.pid,'OPS-101',verification_receipt=task['verification_receipt'])
        result=self.station.batch(self.pid)
        self.assertNotEqual(result['control']['outcome'],'success')
        with self.assertRaises(ContractError):self.station.export(self.pid)

    def test_prestaging_hook_rejects_untyped_pass(self):
        self.station.triage(self.pid)
        work=self.station.prepare(self.pid,'runner','OPS-101')
        with patch('residual.modules.secops.SecOpsModule._sast_scan',return_value=('pass','untyped')):
            with self.assertRaisesRegex(ContractError,'SecOps'):
                self.station.finish(work,{'files':DEMO_FILES['OPS-101']})


if __name__=='__main__':unittest.main()
