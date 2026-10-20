import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from agency.local_tasks import LocalTasks
from agency.tool_agent import ToolAgent
from conversation.conversation_context import ConversationContext
from llm.provider import LLMResult


class ToolAgentTests(unittest.TestCase):
    def test_verified_action_returns_without_extra_inference_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as root:
            tasks = LocalTasks(str(Path(root)/'memory.db'), Path(root)/'workspace')
            call = {'role': 'assistant', 'content': '', 'tool_calls': [
                {'function': {'name': 'create_note', 'arguments': {'text': 'Verificar projeto'}}}]}
            call['tool_calls'] *= 2
            replies = iter([LLMResult(True, '', metadata={'message': call}),
                            LLMResult(True, '', metadata={'message': call}),
                            LLMResult(False, '', 'timeout')])
            core = SimpleNamespace(local_tasks=tasks, settings={}, identity={'name':'Athena','creator':'Rewell'},
                                   conversation_context=ConversationContext(),
                                   llm_provider=SimpleNamespace(generate=lambda *a, **k: next(replies)))
            agent = ToolAgent(core)
            response = agent.chat('Crie uma nota')
            self.assertEqual(len(tasks.list()), 1)
            result = json.loads(tasks.list()[0]['result'])
            self.assertEqual(Path(result['path']).read_text(), 'Verificar projeto\n')
            self.assertIn(result['sha256'], response)
            self.assertIn('completed', response)
            with tasks.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM agent_trace').fetchone()[0], 1)
            with self.assertRaises(ValueError):
                agent.execute('shell_exec', {'command': 'anything'})
            with self.assertRaises(ValueError):
                agent.execute('create_note', {'text': 'x', 'path': '/tmp/x'})

    def test_persistent_facts_are_loaded_without_recent_history(self):
        with tempfile.TemporaryDirectory() as root:
            tasks = LocalTasks(str(Path(root)/'memory.db'), Path(root)/'workspace')
            captured = []
            def generate(*args, **kwargs):
                captured.extend(kwargs['messages'])
                return LLMResult(True, 'Azul', metadata={'message': {'content': 'Azul'}})
            values = {}
            memory = SimpleNamespace(save_definition=lambda s, f: values.update({s:f}),
                                     get_definition=lambda s: values.get(s))
            core = SimpleNamespace(local_tasks=tasks, settings={}, memory=memory,
                identity={'name':'Athena','creator':'Rewell'}, creator_name='Rewell',
                conversation_context=ConversationContext(), llm_provider=SimpleNamespace(generate=generate))
            ToolAgent(core).execute('remember', {'subject':'cor favorita','fact':'azul'})
            agent = ToolAgent(core)
            agent.chat('Qual é minha cor favorita?')
            self.assertTrue(any('Dados persistentes' in m['content'] and 'azul' in m['content'] for m in captured))

    def test_disabled_autonomy_does_not_write(self):
        core = SimpleNamespace(settings={'localAutonomyEnabled':False})
        agent = object.__new__(ToolAgent)
        agent.core = core
        with self.assertRaises(ValueError):
            agent.execute('create_note', {'text': 'x'})


if __name__ == '__main__':
    unittest.main()
