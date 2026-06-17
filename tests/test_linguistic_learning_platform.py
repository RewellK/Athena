import json
import unittest

from language.linguistic_learning_workbench import LinguisticLearningWorkbench, TrainingExample
from language.optional_spacy_analyzer import OptionalSpacyAnalyzer
from language.semantic_frame import SemanticFrameExtractor
from learning.async_llm_teacher_loop import AsyncLlmTeacherLoop, LlmTeacherInsightStore
from learning.learning_interface import LearningInterface
from learning.self_insight_engine import SelfInsightEngine, SelfInsightStore
from reflection.reflection_store import ReflectionEvent


class TeacherLLM:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error
        self.calls = 0

    def generate(self, *_args, **_kwargs):
        self.calls += 1
        if self.error:
            raise self.error

        class Result:
            available = True
            text = json.dumps(self.payload, ensure_ascii=False)

        return Result()


class Settings:
    def __init__(self, values=None):
        self.values = {
            "asyncLlmTeacherEnabled": True,
            "asyncLlmTeacherAutoProcess": False,
            "asyncLlmTeacherTimeoutSeconds": 1,
        }
        self.values.update(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)


class LinguisticLearningPlatformTests(unittest.TestCase):
    def test_training_example_is_saved_listed_and_promoted_to_local_pattern(self):
        workbench = LinguisticLearningWorkbench()
        example = workbench.save_example(TrainingExample(
            utterance="Marina é minha prima.",
            expected_intent="learning_candidate",
            expected_subject="Marina",
            expected_verb="é",
            expected_object="minha prima",
            expected_target="Marina",
            expected_relation_type="cousin_of",
            expected_owner="Rewell",
            status="candidate",
        ))

        pending = workbench.list_examples(status="candidate")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["utterance"], "Marina é minha prima.")

        pattern = workbench.validate_example_as_pattern(example["id"])
        self.assertEqual(pattern["status"], "confirmed")
        self.assertFalse(pattern["requires_human_review"])

        extractor = SemanticFrameExtractor(workbench=workbench, current_user="Rewell")
        frame = extractor.extract("Clara é minha prima.")
        self.assertEqual(frame.intent, "learning_candidate")
        self.assertEqual(frame.subject, "Clara")
        self.assertEqual(frame.verb, "e")
        self.assertEqual(frame.object, "minha prima")
        self.assertEqual(frame.relation_type, "cousin_of")
        self.assertFalse(frame.requires_llm)

    def test_reflection_event_becomes_training_example_and_self_insight(self):
        workbench = LinguisticLearningWorkbench()
        insight_engine = SelfInsightEngine(store=SelfInsightStore())
        event = ReflectionEvent(
            source_message="quero saber oq você sabe sobre ela",
            athena_response="Não entendi com segurança.",
            issue_type="missing_pronoun_resolution",
            suspected_module="ConversationContext",
            explanation="Pronome recente caiu em unknown.",
            suggestion="Resolver pronome por entidade recente.",
            suggested_tests=["Depois de mencionar uma entidade, 'ela' deve resolver localmente."],
        )

        training = workbench.example_from_reflection_event(event)
        insight = insight_engine.create_from_reflection_event(event)

        self.assertEqual(training["source"], "reflection_event")
        self.assertEqual(training["expected_intent"], "entity_query")
        self.assertEqual(training["status"], "candidate")
        self.assertEqual(insight["source"], "reflection_event")
        self.assertEqual(insight["status"], "pending_human_review")
        self.assertTrue(insight["requires_human_review"])

    def test_semantic_frame_covers_learning_pronoun_and_weather_without_spacy_requirement(self):
        extractor = SemanticFrameExtractor(current_user="Rewell")

        learning = extractor.extract("Fernanda é minha namorada.")
        self.assertEqual(learning.subject, "Fernanda")
        self.assertEqual(learning.verb, "e")
        self.assertEqual(learning.object, "minha namorada")
        self.assertEqual(learning.intent, "learning_candidate")
        self.assertEqual(learning.target, "Fernanda")

        pronoun = extractor.extract(
            "quero saber oq você sabe sobre ela",
            context={"recent_entities": [{"name": "Fernanda"}]},
        )
        self.assertEqual(pronoun.intent, "entity_query")
        self.assertEqual(pronoun.target, "Fernanda")
        self.assertEqual(pronoun.resolved_object, "Fernanda")

        weather = extractor.extract("qual o clima amanhã?")
        self.assertEqual(weather.intent, "external_information")
        self.assertEqual(weather.domain, "weather")
        self.assertTrue(weather.requires_evidence)
        self.assertIn("location", weather.required_inputs)

        spacy = OptionalSpacyAnalyzer(model_name="modelo_inexistente_para_teste")
        extractor = SemanticFrameExtractor(current_user="Rewell", spacy_analyzer=spacy)
        frame = extractor.extract("Fernanda é minha namorada.")
        self.assertEqual(frame.intent, "learning_candidate")
        self.assertIn("spacy", frame.context)
        self.assertFalse(frame.context["spacy"]["available"])

    def test_llm_teacher_creates_candidates_not_confirmed_truth(self):
        workbench = LinguisticLearningWorkbench()
        insight_engine = SelfInsightEngine(store=SelfInsightStore())
        llm = TeacherLLM({
            "issue_detected": True,
            "summary": "A pergunta deveria ter resolvido pronome por contexto.",
            "suggested_frame": {
                "raw_text": "me fala dela",
                "intent": "entity_query",
                "target": "Fernanda",
                "subject": "Rewell",
                "verb": "quer saber",
                "object": "dela",
                "scope": "all_known_facts",
            },
            "suggested_learning_strategy": {
                "content": "Quando uma falha de pronome acontecer, criar exemplo de treino e teste.",
                "suggested_action": "Salvar padrão candidato para pronome recente.",
                "suggested_test": "Depois de mencionar Fernanda, 'me fala dela' deve ser entity_query.",
            },
            "suggested_test": "Depois de mencionar Fernanda, 'me fala dela' deve resolver Fernanda.",
            "confidence": 0.41,
        })
        teacher = AsyncLlmTeacherLoop(
            llm_provider=llm,
            store=LlmTeacherInsightStore(),
            workbench=workbench,
            self_insight_engine=insight_engine,
            settings=Settings(),
        )

        teacher.enqueue_turn("me fala dela", "Não entendi.", metadata={"route": "unknown"})
        insight = teacher.process_pending_once()

        self.assertEqual(llm.calls, 1)
        self.assertEqual(insight["status"], "candidate")
        self.assertTrue(insight["requires_human_review"])
        self.assertEqual(workbench.list_examples(status="candidate")[0]["source"], "llm_suggestion")
        self.assertEqual(workbench.list_patterns(status="confirmed"), [])
        self.assertTrue(insight_engine.list_pending())

    def test_learning_interface_lists_and_approves_candidates(self):
        workbench = LinguisticLearningWorkbench()
        insight_engine = SelfInsightEngine(store=SelfInsightStore())
        interface = LearningInterface(workbench=workbench, self_insight_engine=insight_engine)
        example = workbench.save_example(TrainingExample(
            utterance="me fala dela",
            expected_intent="entity_query",
            expected_object="dela",
            expected_scope="all_known_facts",
        ))

        self.assertIn("Exemplos de treino pendentes", interface.respond("pending_training_examples"))
        response = interface.respond("approve_training_example", identifier=example["id"])

        self.assertIn("convertido em padrão local", response)
        self.assertIn("Padrões linguísticos aprendidos", interface.respond("learned_linguistic_patterns"))

    def test_teacher_failure_is_stored_without_raising(self):
        teacher = AsyncLlmTeacherLoop(
            llm_provider=TeacherLLM(error=RuntimeError("offline")),
            store=LlmTeacherInsightStore(),
            settings=Settings(),
        )

        teacher.enqueue_turn("oi", "Olá.", metadata={"route": "greeting"})
        insight = teacher.process_pending_once()

        self.assertEqual(insight["status"], "candidate")
        self.assertIn("falhou sem quebrar", insight["summary"])


if __name__ == "__main__":
    unittest.main()
