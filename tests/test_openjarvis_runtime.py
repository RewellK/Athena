import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from agency.local_tasks import LocalTasks
from capabilities.skill_backend import SkillBackend
from conversation.conversation_context import ConversationContext
from llm.provider import LLMResult
from memory.database import MemoryDB
from integrations.openjarvis.adapter import OpenJarvisRuntime


def call(name, args):
    return LLMResult(True,'',metadata={'message':{'role':'assistant','content':'','tool_calls':[
        {'function':{'name':name,'arguments':args}}]}})


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        tasks=LocalTasks(str(root/'memory.sqlite'),root/'workspace')
        self.memory=MemoryDB(tasks.database)
        self.core=SimpleNamespace(local_tasks=tasks,memory=self.memory,
            settings={'localAutonomyEnabled':True,'autonomousLocalSkillLearning':True},
            identity={'name':'Athena','creator':'Rewell'},creator_name='Rewell',
            conversation_context=ConversationContext(),skill_backend=SkillBackend(tasks),
            llm_provider=None)

    def tearDown(self):
        self.memory.close(); self.temp.cleanup()

    def runtime(self,replies):
        replies=iter(replies)
        self.core.llm_provider=SimpleNamespace(generate=lambda *a,**k:next(replies))
        return OpenJarvisRuntime(self.core)

    def test_real_upstream_multistep_execution(self):
        runtime=self.runtime([call('create_note',{'text':'Minha tarefa'}),call('backup_memory',{}),LLMResult(True,'Concluído')])
        response=runtime.chat('Crie uma nota: Minha tarefa. Faça backup')
        self.assertEqual(len(runtime.events),2)
        self.assertTrue(all(e['ok'] for e in runtime.events),response)
        self.assertEqual(self.core.last_response_metadata['status'],'finished')
        for event in runtime.events:
            result=event['result']['result']
            self.assertEqual(hashlib.sha256(Path(result['path']).read_bytes()).hexdigest(),result['sha256'])
        self.assertIn('SHA-256',response)

    def test_failure_corrected_and_duplicate_does_not_reexecute(self):
        runtime=self.runtime([call('documents',{'operation':'read','name':'ausente.txt'}),
            call('documents',{'operation':'write','name':'plano.txt','content':'Plano executado'}),
            call('documents',{'operation':'write','name':'plano.txt','content':'Plano executado'}),
            LLMResult(True,'Documento criado')])
        response=runtime.chat('Crie um plano')
        self.assertFalse(runtime.events[0]['ok'])
        self.assertTrue(runtime.events[1]['ok'],response)
        self.assertTrue(runtime.events[2]['ok'],response)
        self.assertEqual(len(runtime.catalog.workspace.list()['files']),1)

    def test_evidence_survives_model_failure_and_restart(self):
        runtime=self.runtime([call('create_note',{'text':'Teste'}),LLMResult(False,'','timeout')])
        response=runtime.chat('Crie nota: Teste. Rotina')
        self.assertIn('SHA-256',response)
        self.assertEqual(runtime.store.recent()[0]['status'],'partial')
        runtime.catalog.memory.remember('cor favorita','azul')
        runtime.catalog.memory.remember('cor favorita','verde')
        reloaded=self.runtime([LLMResult(True,'Verde')])
        self.assertEqual(reloaded.catalog.memory.search('cor favorita')['facts'][0]['fact'],'verde')
        self.assertEqual(len(reloaded.catalog.memory.history('cor favorita')['versions']),2)

    def test_workspace_escape_and_autonomy_denied(self):
        runtime=self.runtime([])
        with self.assertRaises(ValueError): runtime.catalog.execute('documents',{'operation':'write','name':'../secret','content':'x'})
        self.core.settings['localAutonomyEnabled']=False
        with self.assertRaises(ValueError): runtime.catalog.execute('create_note',{'text':'x'})
        with self.assertRaises(ValueError): runtime.catalog.execute('shell_exec',{'command':'x'})

    def test_learn_evolve_test_and_rollback(self):
        runtime=self.runtime([call('create_note',{'text':'Rotina original'}),LLMResult(True,'Pronto')])
        runtime.chat('Crie uma nota: Rotina original. Exemplo aceito')
        library=runtime.catalog.procedures
        skill=library.save('rotina',runtime.run_id)
        self.assertTrue(skill['verification']['passed'])
        self.assertEqual(library.run(skill['id'])['completed'],1)
        adapted=library.run(skill['id'],json.dumps([{'step':0,'arguments':{'text':'Rotina adaptada'}}]))
        note_result=adapted['results'][0]['result']
        self.assertEqual(Path(note_result['path']).read_text(),'Rotina adaptada\n')
        self.assertEqual(library.get(skill['id'])['program'][0]['arguments']['text'],'Rotina original')
        variant=library.evolve(skill['id'],json.dumps([{'tool':'create_note','arguments':{'text':'Rotina melhorada'}}]))
        self.assertEqual(variant['parent'],skill['id'])
        self.assertTrue(variant['verification']['isolated'])
        self.assertEqual(library.rollback(variant['id'])['id'],skill['id'])
        with self.assertRaises(ValueError): library.evolve(skill['id'],json.dumps([{'tool':'shell_exec','arguments':{'command':'x'}}]))

    def test_routine_survives_restart_and_runs_without_inference(self):
        runtime=self.runtime([call('create_note',{'text':'Rotina'}),LLMResult(True,'Pronto')])
        runtime.chat('Crie nota: Teste. Rotina')
        skill=runtime.catalog.procedures.save('Rotina',runtime.run_id)
        routine=runtime.catalog.routines.schedule(skill['id'],'60')
        with self.core.local_tasks.connect() as db:
            db.execute('UPDATE agent_routines SET next_due=0 WHERE id=?',(routine['routine_id'],))
        reloaded=self.runtime([])
        before=len(self.core.local_tasks.list())
        self.assertEqual(reloaded.catalog.routines.tick()['executed'],1)
        self.assertEqual(len(self.core.local_tasks.list()),before+1)
        self.assertEqual(reloaded.catalog.routines.list()[0]['status'],'pending')

    def test_queued_goal_executes_only_when_enabled(self):
        values={'localAutonomyEnabled':True,'residentGoalsEnabled':False}
        self.core.settings=SimpleNamespace(values=values,get=lambda k,d=None:values.get(k,d))
        runtime=self.runtime([call('tasks',{'operation':'note','text':'Objetivo residente'}),LLMResult(True,'Feito')])
        self.core.chat=runtime.chat
        runtime.catalog.goals.schedule('Crie uma nota: Objetivo residente')
        self.assertEqual(runtime.catalog.goals.tick(self.core)['executed'],0)
        values['residentGoalsEnabled']=True
        self.assertEqual(runtime.catalog.goals.tick(self.core)['executed'],1)
        self.assertEqual(runtime.catalog.goals.list()[0]['status'],'answered')
        self.assertTrue(any(t['kind']=='note' for t in self.core.local_tasks.list()))

    def test_atomic_attributes_and_reviewed_training_export(self):
        runtime=self.runtime([call('create_note',{'text':'Exemplo aceito'}),LLMResult(True,'Feito')])
        runtime.catalog.memory.remember('Rewell','azul','cor favorita')
        runtime.catalog.memory.remember('Rewell','café','bebida favorita')
        runtime.catalog.memory.remember('Rewell','verde','cor favorita')
        found=runtime.catalog.memory.search('Rewell')['facts']
        self.assertEqual(len(found),2)
        self.assertEqual({f['fact'] for f in found},{'verde','café'})
        runtime.chat('Crie uma nota: Rotina original. Exemplo aceito')
        lab=runtime.catalog.learning_lab
        self.assertEqual(lab.export()['examples'],0)
        lab.review(runtime.run_id,True,'Conteúdo conferido')
        report=lab.export()
        self.assertEqual(report['examples'],1)
        self.assertFalse(report['trained'])
        exported=''.join(Path(p).read_text() for p in report['paths'].values())
        self.assertIn('tool_calls',exported)

    def test_cancel_blocks_next_tool_and_web_rejects_private_addresses(self):
        runtime=self.runtime([])
        runtime.deadline=__import__('time').monotonic()+10
        runtime.cancel()
        self.assertFalse(runtime.allowed('create_note',{'text':'x'}))
        from integrations.openjarvis.web import validate_url
        for url in ['file:///etc/passwd','http://example.com','https://127.0.0.1','https://user:pass@example.com']:
            with self.assertRaises(ValueError): validate_url(url)

    def test_structured_plan_finishes_after_verified_batch(self):
        plan={'actions':[{'tool':'tasks','arguments':{'operation':'note','text':'Plano JSON'}},
                         {'tool':'tasks','arguments':{'operation':'backup'}}], 'reply':'','done':True}
        runtime=self.runtime([LLMResult(True,json.dumps(plan))])
        runtime.engine.planning_mode='structured_plan'
        response=runtime.chat('Crie nota: Plano JSON e backup')
        self.assertEqual(runtime.engine.calls,1)
        self.assertEqual(len(runtime.events),2)
        self.assertTrue(all(event['ok'] for event in runtime.events),response)
        self.assertEqual(self.core.last_response_metadata['status'],'finished')
        self.assertIn('Etapas do plano executadas',response)
        self.assertIn('learned_skill',self.core.last_response_metadata)

    def test_structured_plan_corrects_error_before_finishing(self):
        first={'actions':[{'tool':'files','arguments':{'operation':'read','path':'ausente.txt'}}],'reply':'','done':True}
        second={'actions':[{'tool':'files','arguments':{'operation':'write','path':'plano.txt','content':'Plano corrigido'}}],'reply':'','done':True}
        runtime=self.runtime([LLMResult(True,json.dumps(first)),LLMResult(True,json.dumps(second))])
        runtime.engine.planning_mode='structured_plan'
        response=runtime.chat('Crie plano')
        self.assertEqual(len(runtime.events),2)
        self.assertFalse(runtime.events[0]['ok'])
        self.assertTrue(runtime.events[1]['ok'],response)
        self.assertTrue((self.core.local_tasks.workspace/'plano.txt').exists())

    def test_file_roots_copy_and_no_overwrite(self):
        runtime=self.runtime([])
        files=runtime.catalog.files
        files.execute({'operation':'write','path':'original.txt','content':'Conteúdo real'})
        copied=files.execute({'operation':'copy','path':'original.txt','destination':'copia.txt'})
        self.assertTrue(copied['verified'])
        self.assertEqual(Path(copied['path']).read_text(),'Conteúdo real')
        with self.assertRaises(FileExistsError): files.execute({'operation':'write','path':'original.txt','content':'Trocar'})
        for path in ['../fora.txt','/etc/passwd','.ssh/id_rsa']:
            with self.assertRaises(ValueError): files.execute({'operation':'read','path':path})

    def test_direct_tool_control_needs_no_llm(self):
        runtime=self.runtime([])
        response=runtime.run_tool('tasks',{'operation':'note','text':'Operação offline'})
        self.assertIn('concluído',response)
        self.assertFalse(self.core.last_response_metadata['used_llm'])
        self.assertEqual(runtime.engine.calls,0)

    def test_bad_literal_is_rejected_then_corrected_workflow_is_learned(self):
        first={'actions':[{'tool':'tasks','arguments':{'operation':'note','text':'Revisar projeto }} JSON inválido'}}],'reply':'','done':True}
        repaired={'actions':[{'tool':'tasks','arguments':{'operation':'note','text':'Revisar projeto'}},
                             {'tool':'tasks','arguments':{'operation':'backup'}}],'reply':'','done':True}
        runtime=self.runtime([LLMResult(True,json.dumps(first)),LLMResult(True,json.dumps(repaired))])
        runtime.engine.planning_mode='structured_plan'
        runtime.chat('Crie uma nota: Revisar projeto. Faça backup')
        self.assertFalse(runtime.events[0]['ok'])
        tasks=self.core.local_tasks.list()
        self.assertEqual(len(tasks),2)
        note=next(t for t in tasks if t['kind']=='note')
        self.assertEqual(Path(json.loads(note['result'])['path']).read_text(),'Revisar projeto\n')
        self.assertEqual(self.core.last_response_metadata['status'],'finished_with_errors')
        skills=runtime.catalog.procedures.list()
        self.assertEqual(len(skills),1)
        learned=runtime.catalog.procedures.get(skills[0]['id'])
        self.assertEqual(len(learned['program']),2)
        self.assertTrue(learned['verification']['passed'])

    def test_llm_tool_selection_limits_actor_catalog(self):
        selection={'tools':['create_note','backup_memory'],'reply':''}
        plan={'actions':[{'tool':'create_note','arguments':{'text':'Plano selecionado'}},
                         {'tool':'backup_memory','arguments':{}}],'reply':'','done':True}
        runtime=self.runtime([LLMResult(True,json.dumps(selection)),LLMResult(True,json.dumps(plan))])
        runtime.engine.tool_selection=True
        runtime.engine.planning_mode='structured_plan'
        response=runtime.chat('Crie nota Plano selecionado e backup')
        self.assertEqual(runtime.engine.calls,2)
        self.assertEqual(runtime.engine.selection['tools'],['create_note','backup_memory'])
        self.assertTrue(all(e['ok'] for e in runtime.events),response)
        self.assertEqual(len(runtime.catalog.procedures.list()),1)

    def test_runtime_pause_prevents_background_agent_creation(self):
        from brain.orchestrator import Athena
        core=Athena.__new__(Athena)
        for state in [{'paused':True},{'safe_mode':True}]:
            core.runtime_supervisor=SimpleNamespace(get_status=lambda s=state:s)
            result=core.agent_maintenance()
            self.assertIn(result['status'],{'paused','safe_mode'})
            self.assertFalse(hasattr(core,'agent_runtime'))

    def test_native_actor_receives_only_selected_tools(self):
        replies=iter([LLMResult(True,json.dumps({'tools':['create_note'],'reply':''})),
                      call('create_note',{'text':'Seleção nativa'}),LLMResult(True,'Concluído')])
        observed=[]
        def generate(*args,**kwargs):
            if kwargs.get('tools'):
                observed.append([t['function']['name'] for t in kwargs['tools']])
            return next(replies)
        self.core.llm_provider=SimpleNamespace(generate=generate)
        runtime=OpenJarvisRuntime(self.core)
        runtime.engine.tool_selection=True
        runtime.engine.planning_mode='native_tools'
        runtime.chat('Crie uma nota: Seleção nativa')
        self.assertEqual(observed,[['create_note'],['create_note']])
        self.assertTrue(runtime.events[0]['ok'])

    def test_note_unboxes_transport_string_without_changing_raw_files(self):
        plan={'actions':[{'tool':'create_note','arguments':{'text':'"Revisar projeto"'}},
                         {'tool':'backup_memory','arguments':{}}],'reply':'','done':True}
        runtime=self.runtime([LLMResult(True,json.dumps(plan))])
        runtime.engine.planning_mode='structured_plan'
        runtime.chat('Crie uma nota contendo "Revisar projeto" e backup')
        self.assertTrue(all(event['ok'] for event in runtime.events))
        task=next(t for t in self.core.local_tasks.list() if t['kind']=='note')
        self.assertEqual(Path(json.loads(task['result'])['path']).read_text(),'Revisar projeto\n')
        skill=runtime.catalog.procedures.list()[0]
        replay=runtime.catalog.procedures.run(skill['id'])
        self.assertEqual(Path(replay['results'][0]['result']['path']).read_text(),'Revisar projeto\n')
        raw=runtime.catalog.files.execute({'operation':'write','path':'aspas.txt','content':'"Revisar projeto"'})
        self.assertEqual(Path(raw['path']).read_text(),'"Revisar projeto"')

    def test_foreground_presence_runs_local_work_and_separates_background_policy(self):
        from runtime.foreground_presence import ForegroundPresence
        state={'paused':False,'safe_mode':False}
        self.core.runtime_supervisor=SimpleNamespace(get_status=lambda:state,heartbeat=lambda:None)
        self.core.settings.update(computerToolsEnabled=True,allowExternalRequests=True,useLLM=False)
        self.core.llm_provider=SimpleNamespace(generate=lambda *a,**k:None)
        presence=ForegroundPresence(self.core)
        try:
            self.assertFalse(presence.view.settings.get('computerToolsEnabled'))
            self.assertFalse(presence.view.settings.get('allowExternalRequests'))
            self.assertTrue(self.core.settings.get('computerToolsEnabled'))
            task=self.core.local_tasks.schedule('note','Lembrete com interface aberta')
            presence.tick()
            self.assertEqual(next(t for t in self.core.local_tasks.list() if t['id']==task)['status'],'completed')
            self.core.settings['localAutonomyEnabled']=False
            self.assertFalse(presence.view.settings.get('localAutonomyEnabled'))
        finally:presence.stop()

    def test_verified_final_batch_does_not_need_an_extra_turn(self):
        self.core.settings['agentMaxTurns']=1
        plan={'actions':[{'tool':'create_note','arguments':{'text':'Última etapa'}},
                         {'tool':'backup_memory','arguments':{}}],'reply':'','done':True}
        runtime=self.runtime([LLMResult(True,json.dumps(plan))])
        runtime.engine.planning_mode='structured_plan'
        runtime.chat('Crie nota Última etapa e backup')
        self.assertEqual(self.core.last_response_metadata['status'],'finished')
        self.assertTrue(self.core.last_response_metadata['completed_at_limit'])
        self.assertEqual(len(self.core.local_tasks.list()),2)

    def test_upstream_pin_is_intact(self):
        root=Path(__file__).resolve().parents[1]/'third_party/openjarvis'
        manifest=json.loads((root/'UPSTREAM.json').read_text())
        for path,digest in manifest['files_sha256'].items():
            self.assertEqual(hashlib.sha256((root/'openjarvis'/path).read_bytes()).hexdigest(),digest,path)


if __name__=='__main__': unittest.main()
