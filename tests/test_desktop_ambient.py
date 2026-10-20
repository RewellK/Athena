import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from agency.local_tasks import LocalTasks
from desktop.paths import prepare_home
from desktop.service import specification
from voice.ambient import SpeechSegmenter,AmbientStore,AmbientListener
from llm.provider import LLMResult


class DesktopAmbientTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.tasks=LocalTasks(self.root/'memory.sqlite',self.root/'workspace')
    def tearDown(self):self.temp.cleanup()
    def test_external_home_bootstrap_preserves_settings(self):
        home=self.root/'data'
        with patch.dict(os.environ,{'ATHENA_HOME':str(home)}):
            prepare_home();path=home/'config/settings.json';path.write_text('{"custom":true}')
            prepare_home();self.assertEqual(json.loads(path.read_text()),{'custom':True})
            self.assertTrue((home/'personality/identity.json').exists())
    def test_service_runs_binary_in_private_home_without_python_script(self):
        config=specification('/Applications/Athena.app/Contents/MacOS/Athena',self.root)
        self.assertEqual(config['ProgramArguments'],['/Applications/Athena.app/Contents/MacOS/Athena','--resident'])
        self.assertEqual(config['EnvironmentVariables']['ATHENA_HOME'],str(self.root))
        self.assertNotIn('Sockets',config)
    def test_signal_gate_bounds_audio_and_ignores_silence(self):
        import numpy as np
        gate=SpeechSegmenter()
        for _ in range(100):self.assertIsNone(gate.feed(np.zeros(1600)))
        self.assertIsNone(gate.feed(np.ones(1600)*.1))
        segment=None
        for _ in range(8):segment=gate.feed(np.zeros(1600))
        self.assertIsNotNone(segment);self.assertLessEqual(len(segment),16000*12)
    def test_observed_fact_requires_named_subject_and_literal_evidence(self):
        store=AmbientStore(self.tasks)
        fact={'subject':'Fernanda','attribute':'aniversário','fact':'20/10','evidence':'Fernanda faz aniversário em 20/10','confidence':.99}
        self.assertTrue(store.observe(fact,fact['evidence']))
        self.assertFalse(store.observe(fact,'Meu aniversário é amanhã'))
        self.assertFalse(store.observe(fact,fact['evidence']))
        self.assertEqual(store.facts()[0]['status'],'observed')
        store.clear();self.assertEqual(store.facts(),[])
    def listener(self,decision,facts=None):
        decision.setdefault('kind','question')
        settings={'ambientListeningEnabled':True,'ambientSpeakAnswers':False,'useLLM':True}
        core=SimpleNamespace(settings=settings,local_tasks=self.tasks,
            runtime_supervisor=SimpleNamespace(get_status=lambda:{}),
            agent_runtime=SimpleNamespace(catalog=SimpleNamespace(memory=SimpleNamespace(search=lambda *a,**k:{'facts':facts or []}))))
        presence=SimpleNamespace(interacting=__import__('threading').Event())
        listener=AmbientListener(core,presence)
        listener.provider=SimpleNamespace(settings=settings,generate=lambda *a,**k:LLMResult(True,json.dumps(decision)))
        return listener
    def test_answer_is_assembled_from_known_memory_not_model_invented_text(self):
        fact={'id':1,'subject':'Fernanda','attribute':'aniversário','fact':'20/10'}
        listener=self.listener({'answer':True,'confidence':.99,'evidence_ids':['m1'],'facts':[],'needs_speaker':False},[fact])
        result=listener.process_text('Quando é o aniversário da Fernanda?')
        self.assertIn('20/10',result['answer'])
        self.assertEqual(result['observations'],0)
    def test_unknown_date_is_not_invented_and_speaker_is_clarified(self):
        listener=self.listener({'answer':True,'confidence':.99,'evidence_ids':['invented'],'facts':[],'needs_speaker':False})
        self.assertIn('não tenho',listener.process_text('Quando é o aniversário da minha namorada?')['answer'])
        listener=self.listener({'answer':False,'confidence':.99,'evidence_ids':[],'facts':[],'needs_speaker':True})
        result=listener.process_text('Meu aniversário é dia vinte.')
        self.assertIn('Quem está falando',result['answer'])
        self.assertEqual(result['observations'],0)
    def test_factual_statement_does_not_trigger_an_answer(self):
        listener=self.listener({'kind':'statement','answer':True,'confidence':.99,'evidence_ids':[],'facts':[],'needs_speaker':False})
        self.assertEqual(listener.process_text('Fernanda faz aniversário em vinte de outubro.')['answer'],'')

    def test_unconfirmed_observations_are_qualified_in_speech(self):
        listener=self.listener({'answer':True,'confidence':.99,'evidence_ids':[],'facts':[],'needs_speaker':False})
        fact={'subject':'Fernanda','attribute':'aniversário','fact':'20/10','evidence':'Fernanda nasceu em 20/10','confidence':.99}
        listener.store.observe(fact,fact['evidence']);item=listener.store.facts()[0]
        listener.provider.generate=lambda *a,**k:LLMResult(True,json.dumps({'kind':'question','answer':True,'confidence':.99,'evidence_ids':['m1'],'facts':[],'needs_speaker':False}))
        self.assertIn('ainda não confirmada',listener.process_text('Quando é o aniversário da Fernanda?')['answer'])

if __name__=='__main__':unittest.main()

class SecurityLearningTests(unittest.TestCase):
    def test_reported_identity_error_tightens_policy_and_persists(self):
        from runtime.security_learning import SecurityLearning
        with tempfile.TemporaryDirectory() as tmp:
            tasks=LocalTasks(Path(tmp)/'test.db',Path(tmp)/'workspace')
            learning=SecurityLearning(tasks)
            self.assertEqual(learning.threshold(),.8)
            learning.record('uncertain_voice')
            self.assertEqual(learning.threshold(),.8)
            changed=learning.record('wrong_speaker_reported')
            self.assertTrue(changed['policy_changed'])
            self.assertEqual(SecurityLearning(tasks).threshold(),.84)
            for _ in range(10):learning.record('wrong_speaker_reported')
            self.assertEqual(learning.threshold(),.96)
            self.assertIn('voice_is_not_authorization',learning.status()['invariants'])

class ExperienceWorkshopTests(unittest.TestCase):
    def test_procedure_proposal_is_tested_before_approval_then_evolves(self):
        from memory.database import MemoryDB
        from capabilities.skill_backend import SkillBackend
        from conversation.conversation_context import ConversationContext
        from integrations.openjarvis.adapter import OpenJarvisRuntime
        from learning.experience_workshop import ExperienceWorkshop
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tasks=LocalTasks(root/'memory.sqlite',root/'workspace');memory=MemoryDB(tasks.database)
            core=SimpleNamespace(local_tasks=tasks,memory=memory,settings={'localAutonomyEnabled':True,'autonomousLocalSkillLearning':True},identity={'name':'Athena'},creator_name='Rewell',conversation_context=ConversationContext(),llm_provider=None,skill_backend=SkillBackend(tasks))
            try:
                core.agent_runtime=OpenJarvisRuntime(core)
                library=core.agent_runtime.catalog.procedures
                old=library.create('Nota de teste',[{'tool':'create_note','arguments':{'text':'Antes'}}])
                workshop=ExperienceWorkshop(core)
                proposal=workshop.save_proposal({'problem':'Texto incompleto','why':'Correção de procedimento','change':'Nota atualizada','kind':'procedure','skill_id':old['id'],'program_json':json.dumps([{'tool':'create_note','arguments':{'text':'Depois'}}])})
                self.assertEqual(proposal['status'],'tested')
                self.assertEqual(library.get(old['id'])['status'],'active')
                self.assertTrue(workshop.approve(proposal['id'])['applied'])
                self.assertEqual(library.get(old['id'])['status'],'retired')
                self.assertEqual(sum(p['status']=='active' for p in library.list()),1)
            finally:memory.close()
    def test_code_proposal_is_exported_without_claiming_application(self):
        from learning.experience_workshop import ExperienceWorkshop
        with tempfile.TemporaryDirectory() as tmp:
            tasks=LocalTasks(Path(tmp)/'memory.sqlite',Path(tmp)/'workspace')
            workshop=ExperienceWorkshop(SimpleNamespace(local_tasks=tasks))
            proposal=workshop.save_proposal({'problem':'Exemplo de falha','why':'Precisa investigar','change':'Inspecionar módulo','kind':'code','skill_id':'','program_json':''})
            result=workshop.approve(proposal['id'])
            self.assertFalse(result['applied']);self.assertTrue(Path(result['exported']).is_file())


class AutomaticReviewTests(unittest.TestCase):
    def test_repeated_experiences_create_one_proposal_and_notification(self):
        from learning.experience_workshop import ExperienceWorkshop
        with tempfile.TemporaryDirectory() as tmp:
            tasks=LocalTasks(Path(tmp)/'test.sqlite',Path(tmp)/'workspace')
            workshop=ExperienceWorkshop(SimpleNamespace(local_tasks=tasks,settings={}))
            for index in range(3):workshop.observe('execution_difficulty',str(index),'partial')
            proposal=workshop.tick()
            self.assertEqual(proposal['status'],'proposed')
            workshop.tick()
            self.assertEqual(len(workshop.report()['proposals']),1)
            self.assertEqual(len(tasks.list()),1)


class GuiDispatchTests(unittest.TestCase):
    def test_worker_result_waits_for_ui_dispatch(self):
        import queue
        from background_tasks.task_runner import BackgroundTaskRunner
        callbacks=queue.Queue();seen=[]
        runner=BackgroundTaskRunner(callback_dispatch=callbacks.put)
        try:
            runner.submit(lambda:42,on_success=seen.append)
            callback=callbacks.get(timeout=2)
            self.assertEqual(seen,[])
            callback();self.assertEqual(seen,[42])
        finally:runner.shutdown()
