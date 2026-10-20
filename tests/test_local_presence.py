import json
import io
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
from unittest.mock import patch

from bootstrap import AthenaBootstrap
from conversation.intent_resolution_engine import IntentResolutionEngine
from conversation.conversation_context import ConversationContext
from conversation.recent_store import RecentConversationStore
from llm.provider import OllamaProvider
from memory.database import MemoryDB
from runtime.background_cognition_loop import BackgroundCognitionLoop
from runtime.process_lease import foreground_active, foreground_session, lease
from runtime.runtime_supervisor import RuntimeSupervisor
from runtime.runtime_state_store import RuntimeStateStore
from semantic_language import ASLInterpreter


class LocalPresenceTests(unittest.TestCase):
    def test_resolved_intent_does_not_trigger_second_relevance_llm_call(self):
        from conversation.conversation_router import ConversationRouter
        router=ConversationRouter(settings={'conversationRoutingMode':'llm_first'})
        with patch.object(router.relevance_engine,'evaluate') as evaluate:
            self.assertEqual(router._evaluate_relevance('crie nota',{'route':'agency'},{},None),{})
        evaluate.assert_not_called()

    def test_memory_lifecycle_deduplicates_archives_and_preserves_provenance(self):
        from memory_manager.memory_manager import MemoryManager
        with tempfile.TemporaryDirectory() as root:
            memory=MemoryDB(str(Path(root)/'memory.db'))
            try:
                manager=MemoryManager(memory,settings={'shortTermMemoryHours':2,'midTermMemoryDays':3})
                memory.save_short_term_memory('Projeto Aurora usa SQLite',20)
                memory.save_short_term_memory('Projeto Boreal usa SQLite',20)
                self.assertEqual(manager.promote_short_to_mid(),0)
                original=memory.save_short_term_memory('Projeto Aurora usa SQLite',20)
                self.assertEqual(len(memory.list_short_term_memory()),2)
                self.assertEqual(manager.promote_short_to_mid(),1)
                mid=memory.list_mid_term_memory()[0]
                self.assertEqual(mid[1],'Projeto Aurora usa SQLite')
                self.assertEqual(mid[3],2)
                self.assertEqual(memory.conn.execute('SELECT short_id,mid_id,observations FROM memory_evidence').fetchone(),(original,mid[0],2))
                manager.promote_mid_to_long(mid[0],mid[1])
                metadata=memory.list_long_term_memory_with_metadata()[0][-1]
                self.assertEqual(metadata['source_mid_id'],mid[0])
                memory.save_short_term_memory('Memória temporária vencida',0,hours_to_live=-1)
                self.assertEqual(memory.expire_short_term_memory(),1)
                self.assertEqual(memory.expire_short_term_memory(),0)
                self.assertEqual(len(memory.list_short_term_memory(include_expired=True)),3)
                self.assertEqual(memory.count_real_long_term_memory(),1)
                matches=manager.retrieve('Aurora')
                self.assertTrue(any(item['confirmed'] for item in matches))
                self.assertEqual(manager.retrieve('vencida'),[])
            finally: memory.close()

    def test_old_memory_schema_migrates_twice_without_loss(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            path=str(Path(root)/'memory.db')
            connection=sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE short_term_memory(id INTEGER PRIMARY KEY,content TEXT NOT NULL,content_hash TEXT UNIQUE,created_at TEXT,expires_at TEXT,importance_score INTEGER,processed INTEGER DEFAULT 0);
                CREATE TABLE mid_term_memory(id INTEGER PRIMARY KEY,summary TEXT UNIQUE,topics TEXT,source_count INTEGER,created_at TEXT,expires_at TEXT,importance_score INTEGER,promoted INTEGER DEFAULT 0);
                CREATE TABLE long_term_memory(id INTEGER PRIMARY KEY,content TEXT,content_hash TEXT UNIQUE,source TEXT,importance_score INTEGER,created_at TEXT);
                INSERT INTO long_term_memory VALUES(1,'Projeto Aurora persiste','hash-old','manual',80,'2026-01-01');
            """)
            connection.commit(); connection.close()
            for _ in range(2):
                memory=MemoryDB(path)
                try:
                    self.assertEqual(memory.count_real_long_term_memory(),1)
                    self.assertEqual(len(memory.search_memory('Aurora')),1)
                finally: memory.close()

    def test_skill_backend_tests_then_reuses_approved_skill_without_llm(self):
        from agency.local_tasks import LocalTasks
        from capabilities.skill_backend import SkillBackend
        with tempfile.TemporaryDirectory() as root:
            tasks=LocalTasks(str(Path(root)/'memory.db'),Path(root)/'workspace')
            backend=SkillBackend(tasks)
            recipe={'name':'Registrar revisão com segurança','steps':[{'kind':'note','text':'Revisar resultados'},{'kind':'backup'}]}
            candidate=backend.propose(recipe)
            with self.assertRaises(ValueError): backend.run(candidate['id'])
            self.assertTrue(backend.verify(candidate['id'])['passed'])
            self.assertEqual(tasks.list(), [])
            with patch.object(backend,'design',return_value={'status':'awaiting_review','skill':candidate,'verification':{'passed':True}}):
                learned=backend.learn('rotina local',allow_local_policy=True)
            self.assertEqual(learned['status'],'active')
            self.assertEqual(learned['skill']['activation_origin'],'verified_local_composition_policy')
            with self.assertRaises(ValueError): backend.activate(candidate['id'],'wrong')
            backend.activate(candidate['id'],candidate['digest'])
            restored=SkillBackend(tasks)
            self.assertEqual(restored.run(candidate['id'])['execution']['completed'],2)
            with self.assertRaises(ValueError): backend.propose({'name':'Enviar email','steps':[{'kind':'email','text':'oi'}]})

    def test_llm_uncertainty_asks_instead_of_learning_from_local_guess(self):
        from conversation.conversation_router import ConversationRouter
        router = ConversationRouter(settings={'conversationRoutingMode':'llm_first'})
        with patch.object(router.intent_resolution_engine,'resolve',return_value={'available':True,'intent':'unknown','confidence':0.0}), patch.object(router,'_cognitive_fallback_route') as fallback:
            result = router.route('Ele mudou de ideia.')
        fallback.assert_not_called()
        self.assertTrue(result['needs_clarification'])
        self.assertNotEqual(result['route'],'learning')

    def test_nonfinite_confidence_cannot_authorize_route(self):
        self.assertEqual(IntentResolutionEngine()._confidence('NaN'), 0.0)
        self.assertEqual(IntentResolutionEngine()._confidence('Infinity'), 0.0)

    def test_service_preserves_virtual_environment_python_path(self):
        from scripts.macos_service import specification
        with tempfile.TemporaryDirectory() as root:
            executable = Path(root)/'venv/bin/python'
            executable.parent.mkdir(parents=True)
            executable.symlink_to('/usr/bin/python3')
            self.assertEqual(specification(str(executable))['ProgramArguments'][0], str(executable))

    def test_reviewed_read_operation_runs_without_llm_and_conflicts_abstain(self):
        from language.linguistic_learning_workbench import LinguisticLearningWorkbench
        from conversation.conversation_router import ConversationRouter
        bench = LinguisticLearningWorkbench()
        payload = {'utterance':'Conte sobre o projeto Aurora', 'expected_intent':'entity_query', 'expected_target':'Aurora',
            'expected_frame':{'target_type':'entity'}, 'context':{'reusable_without_context':True}}
        example = bench.save_example(payload)
        self.assertIsNone(bench.resolve_reviewed(payload['utterance']))
        bench.validate_example_as_pattern(example['id'])
        router = ConversationRouter(settings={'useLLM':False})
        router.intent_resolution_engine.workbench = bench
        route = router.route('Conte sobre o projeto Aurora!')
        self.assertEqual(route['source'],'local_reviewed_example')
        self.assertEqual(route['target'],'Aurora')
        conflict = bench.save_example(dict(payload,expected_target='Outro'))
        bench.validate_example_as_pattern(conflict['id'])
        self.assertIsNone(bench.resolve_reviewed(payload['utterance']))

    def test_real_tasks_execute_and_survive_restart(self):
        from agency.local_tasks import LocalTasks
        with tempfile.TemporaryDirectory() as root:
            database = str(Path(root)/'memory.db')
            db = MemoryDB(database)
            AthenaBootstrap(db).run()
            db.close()
            workspace = Path(root)/'workspace'
            tasks = LocalTasks(database,workspace)
            note = tasks.schedule('note','Uma nota real')
            reminder = tasks.schedule('reminder','Revisar o projeto')
            backup = tasks.schedule('backup')
            cancelled = tasks.schedule('note','Não executar')
            self.assertTrue(tasks.cancel(cancelled))
            restored = LocalTasks(database,workspace)
            result = restored.run_once()
            self.assertEqual(result['completed'], 3)
            self.assertEqual((workspace/'notes'/f'{note}.txt').read_text(), 'Uma nota real\n')
            self.assertTrue((workspace/'inbox'/f'{reminder}.txt').exists())
            import sqlite3
            snapshot = sqlite3.connect(workspace/'backups'/f'{backup}.sqlite')
            try:
                self.assertEqual(snapshot.execute('PRAGMA quick_check').fetchone()[0], 'ok')
            finally:
                snapshot.close()
            self.assertEqual(restored.run_once()['completed'], 0)
            self.assertEqual(next(x for x in restored.list() if x['id']==cancelled)['status'], 'cancelled')
            with self.assertRaises(ValueError):
                restored.schedule('shell','anything')
            with self.assertRaises(ValueError):
                restored.schedule('note','')

    def test_ambiguity_asks_before_learning(self):
        from tests.test_v12_5 import make_athena
        with tempfile.TemporaryDirectory() as root:
            athena = make_athena(Path(root))
            try:
                with patch.object(athena, '_handle_learning_route') as learn:
                    text = athena._delegate_conversation_route(1, {'route':'learning', 'needs_clarification':True,
                        'clarification_question':'A quem você se refere?'}, 'Ele mudou.')
                learn.assert_not_called()
                self.assertEqual(text, 'A quem você se refere?')
            finally:
                athena.memory.close()

    def test_reviewed_examples_persist_and_feed_interpretation(self):
        from language.linguistic_learning_workbench import LinguisticLearningWorkbench
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root)/'training.json')
            bench = LinguisticLearningWorkbench(path)
            example = bench.save_example({'utterance':'Explique a fotossíntese', 'expected_intent':'reasoning'})
            self.assertEqual(bench.interpretation_examples('Explique a gravidade'), [])
            bench.validate_example_as_pattern(example['id'])
            restored = LinguisticLearningWorkbench(path)
            learned = restored.interpretation_examples('Explique a gravidade')
            self.assertEqual(learned[0]['intent'], 'reasoning')
            engine = IntentResolutionEngine()
            engine.workbench = restored
            self.assertIn('fotossíntese', engine._build_prompt('Explique a gravidade'))

    def test_llm_first_avoids_legacy_phrase_identity_routing(self):
        from conversation.conversation_router import ConversationRouter
        router = ConversationRouter(settings={'conversationRoutingMode':'llm_first', 'fastPathEnabled':True})
        self.assertIsNone(router._fast_route('Quem é você?'))
        self.assertIsNotNone(router._fast_route('comando status'))

    def test_fallback_only_when_model_missing_and_options(self):
        provider = OllamaProvider({'ollamaModel':'new','ollamaFallbackModels':['old']})
        missing = urllib.error.HTTPError('local',404,'missing',{},io.BytesIO(b'missing'))
        with patch.object(provider, '_json', side_effect=[missing, {'response':'resposta'}]) as request:
            result = provider.generate('oi', response_format='json')
        self.assertTrue(result.available)
        self.assertTrue(result.metadata['fallback'])
        payload = request.call_args.args[2]
        self.assertEqual(payload['model'], 'old')
        self.assertFalse(payload['think'])
        self.assertEqual(payload['format'], 'json')
        self.assertEqual(payload['options']['num_ctx'], 4096)

    def test_timeout_has_no_retry_and_circuit_prevents_repeated_delay(self):
        provider = OllamaProvider({})
        with patch.object(provider, '_json', side_effect=TimeoutError('slow')) as request:
            self.assertFalse(provider.generate('oi').available)
            self.assertFalse(provider.generate('oi').available)
            self.assertEqual(request.call_count, 1)

    def test_turn_budget_shared_across_calls(self):
        provider = OllamaProvider({})
        with patch.object(provider, '_json', return_value={'response':'ok'}) as request:
            with provider.turn_budget(.02):
                self.assertTrue(provider.generate('a').available)
                time.sleep(.03)
                self.assertFalse(provider.generate('b').available)
            self.assertEqual(request.call_count, 1)

    def test_remote_endpoint_rejected_before_network(self):
        provider = OllamaProvider({'ollamaUrl':'http://example.org/api/generate'})
        with patch.object(provider._opener, 'open') as request:
            self.assertFalse(provider.generate('private').available)
            request.assert_not_called()

    def test_health_requires_configured_model_not_just_daemon(self):
        provider = OllamaProvider({'ollamaModel':'new','ollamaFallbackModels':[]})
        with patch.object(provider, '_json', return_value={'models':[{'name':'other'}]}):
            self.assertFalse(provider.health_check()['available'])

    def test_intent_string_false_does_not_grant_learning(self):
        result = IntentResolutionEngine()._normalize({'intent':'learning','should_learn':'false','requires_tool':'true'})
        self.assertFalse(result['should_learn'])
        self.assertFalse(result['requires_tool'])

    def test_recent_context_survives_restart_without_confirming_knowledge(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root)/'memory.db')
            context = ConversationContext(store=RecentConversationStore(path, limit=2))
            context.add_user_message('primeiro')
            context.add_athena_message('segundo')
            context.add_user_message('terceiro')
            restored = ConversationContext(store=RecentConversationStore(path, limit=2))
            self.assertEqual([x['content'] for x in restored.recent()], ['segundo','terceiro'])
            expired = RecentConversationStore(path, ttl_hours=0)
            self.assertEqual(expired.load(), [])

    def test_exclusive_core_and_foreground_priority(self):
        with tempfile.TemporaryDirectory() as root:
            with foreground_session(root):
                self.assertTrue(foreground_active(root))
                with lease(Path(root)/'core.lock', blocking=False) as acquired:
                    self.assertFalse(acquired)
            self.assertFalse(foreground_active(root))

    def test_background_loop_survives_cycle_failure(self):
        class Supervisor:
            calls = 0
            def run_once(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError('simulated')
        supervisor = Supervisor()
        loop = BackgroundCognitionLoop(supervisor, interval_seconds=.01)
        with self.assertLogs('runtime.background_cognition_loop', level='ERROR'):
            loop.start()
            time.sleep(.06)
            loop.stop()
        self.assertGreater(supervisor.calls, 1)

    def test_restart_recovers_stale_active_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            store = RuntimeStateStore(str(Path(root)/'state.json'))
            store.set_state('processing', reason='crash')
            supervisor = RuntimeSupervisor(state_store=store, settings={'runtimeAuditLogPath':str(Path(root)/'audit.jsonl'),'runtimeTaskStorePath':str(Path(root)/'tasks.json')})
            self.assertEqual(supervisor.start(background=False)['state'], 'idle')
            supervisor.stop()

    def test_asl_requires_exact_approval_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root)/'memory.db')
            db = MemoryDB(path)
            try:
                AthenaBootstrap(db).run()
                program = {'asl':'1','op':'relation.add','args':{'source':'A','relation':'parte_de','target':'B'}}
                asl = ASLInterpreter(db)
                proposed = asl.execute(program)
                self.assertEqual(proposed['status'], 'approval_required')
                self.assertEqual(db.find_relationships(source='A'), [])
                asl.execute(program, proposed['digest'])
                asl.execute(program, proposed['digest'])
                self.assertEqual(len(db.find_relationships(source='A')), 1)
                changed = dict(program, args=dict(program['args'], target='C'))
                self.assertEqual(asl.execute(changed, proposed['digest'])['status'], 'approval_required')
                with self.assertRaises(ValueError):
                    asl.execute({'asl':'1','op':'shell','args':{'command':'anything'}})
            finally:
                db.close()
            db = MemoryDB(path)
            try:
                self.assertEqual(len(db.find_relationships(source='A')), 1)
            finally:
                db.close()


if __name__ == '__main__':
    unittest.main()
