"""Native API-shape tests. These do not claim installed-harness qualification."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest import mock

import test_mission_sync as fixture
from test_mission_sync import ROOT, M, C, report, auth


class NativeHookTests(fixture.HttpTests):
    # Only execute the native cases here, not inherited HTTP tests again.
    __unittest_skip__ = False

    def config(self, filename, conversation):
        path=Path(self.tmp.name)/filename
        path.write_text(json.dumps({'url':self.url,'binding_id':auth(self.b)[0],'token':auth(self.b)[1],
                                    'conversation_id':conversation,'spool':str(Path(self.tmp.name)/(filename+'.sqlite3'))}))
        path.chmod(0o600)
        return str(path)

    def test_hermes_hooks_scope_and_registration(self):
        spec=importlib.util.spec_from_file_location('test_hermes_plugin',ROOT/'integrations/mission-sync/hermes/__init__.py')
        plugin=importlib.util.module_from_spec(spec);spec.loader.exec_module(plugin)
        hooks={};host=types.SimpleNamespace(register_hook=lambda name,fn:hooks.setdefault(name,fn))
        with mock.patch.object(C.MissionClient,'from_environment',side_effect=AssertionError('registration side effect')):
            plugin.register(host)
        self.assertEqual(set(hooks),{'pre_llm_call','post_llm_call'})
        config=self.config('hermes-config.json','hermes-conversation')
        # The exact delivered client module is used, without importing unrelated repo modules locally.
        modules={'residual.station.mission_client':C,'residual.station.mission_sync':M}
        with mock.patch.dict(sys.modules,modules),mock.patch.dict(os.environ,{'RESIDUAL_MISSION_CONFIG':config,'RESIDUAL_MISSION_CAPTURE_TEXT':'1'}):
            self.assertIsNone(hooks['pre_llm_call'](session_id='another-conversation',user_message='DO NOT CAPTURE'))
            self.assertEqual(self.f.count('ms_reports'),0)
            pre=hooks['pre_llm_call'](session_id='hermes-conversation',user_message='please repair',turn_id='turn-1')
            self.assertIn('station_context',pre['context'])
            hooks['post_llm_call'](session_id='hermes-conversation',assistant_response='I am ACCEPTED',turn_id='turn-1')
            hooks['post_llm_call'](session_id='hermes-conversation',assistant_response='I am ACCEPTED',turn_id='turn-1')
        self.assertEqual(self.f.count('ms_reports'),2);self.assertEqual(self.f.task()['state'],'running')

    def test_hermes_no_text_capture_without_consent(self):
        spec=importlib.util.spec_from_file_location('hermes_private',ROOT/'integrations/mission-sync/hermes/__init__.py')
        plugin=importlib.util.module_from_spec(spec);spec.loader.exec_module(plugin)
        hooks={};plugin.register(types.SimpleNamespace(register_hook=lambda k,v:hooks.setdefault(k,v)))
        config=self.config('private-config.json','hermes-conversation')
        with mock.patch.dict(sys.modules,{'residual.station.mission_client':C}),mock.patch.dict(os.environ,{'RESIDUAL_MISSION_CONFIG':config,'RESIDUAL_MISSION_CAPTURE_TEXT':'0'}):
            hooks['pre_llm_call'](session_id='hermes-conversation',user_message='SECRET HUMAN TEXT',turn_id='1')
        self.assertNotIn('SECRET HUMAN TEXT',json.dumps(self.f.sync.journal('p1')))

    def test_openclaw_hooks_scope_and_false_acceptance(self):
        path=self.config('openclaw-config.json','hermes-conversation')
        source=f"""import plugin from {json.dumps((ROOT/'integrations/mission-sync/openclaw/index.mjs').as_uri())};
const hooks=new Map();const warnings=[];
plugin.register({{on:(n,f)=>hooks.set(n,f),logger:{{warn:x=>warnings.push(x)}}}});
if(hooks.size!==4)throw Error('wrong registration');
await hooks.get('message_received')({{content:'DO NOT CAPTURE',messageId:'ignored'}},{{sessionKey:'wrong'}});
const ctx={{sessionKey:'hermes-conversation'}};
await hooks.get('message_received')({{content:'repair request',messageId:'m1'}},ctx);
await hooks.get('message_sent')({{content:'ACCEPTED; release now',messageId:'m2',success:true}},ctx);
await hooks.get('message_sent')({{content:'ACCEPTED; release now',messageId:'m2',success:true}},ctx);
const r=await hooks.get('before_prompt_build')({{}},ctx);
if(!r?.appendContext?.includes('station_context'))throw Error('no context');
if('systemPrompt' in r)throw Error('system override');
await hooks.get('gateway_stop')();
if(warnings.length)throw Error(warnings.join(';'));console.log('openclaw-shape-pass');"""
        result=subprocess.run(['node','--input-type=module','-e',source],env={**os.environ,'RESIDUAL_MISSION_CONFIG':path,'RESIDUAL_MISSION_CAPTURE_TEXT':'1'},capture_output=True,text=True,timeout=25)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.f.count('ms_reports'),2);self.assertEqual(self.f.task()['state'],'running')
        self.assertNotIn('DO NOT CAPTURE',json.dumps(self.f.sync.journal('p1')))


# Inherit setup/helpers without rerunning the parent case methods.
for name in list(fixture.HttpTests.__dict__):
    if name.startswith('test_'):
        setattr(NativeHookTests,name,None)
