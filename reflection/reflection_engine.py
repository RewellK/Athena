import json
import re
import time
import unicodedata
from datetime import datetime, timedelta

from reflection.reflection_store import ReflectionEvent, ReflectionStore


class ReflectionEngine:
    """
    Reflection is evidence-driven.
    It does not map user phrases to fixed behaviours. The Orchestrator routes
    reflection requests through structured intention.

    V12.7-pre adds local self-audit. The engine can observe a completed turn,
    detect likely failures, and store improvement hypotheses for human review.
    """

    SIMPLE_LOCAL_ROUTES = {
        "greeting",
        "small_talk",
        "conversation",
        "identity",
        "self_identity",
        "user_identity",
        "capability",
        "technical_capability",
        "limitation_query",
        "external_information",
        "system",
        "pending_confirmation",
        "teach_intent",
    }

    def __init__(self, memory, identity, context_builder=None, llm_provider=None, store=None, settings=None, logger=None):
        self.memory = memory
        self.identity = identity
        self.context_builder = context_builder
        self.llm_provider = llm_provider
        self.settings = settings
        self.logger = logger
        self.store = store or ReflectionStore(
            path=self._setting("reflectionStorePath", "logs/reflection_events.jsonl"),
            logger=logger,
        )
        self._session_events = []

    def respond(self, user_input):
        evidence = self._reflection_evidence()
        if self._wants_local_report(user_input):
            return self._local_improvement_report(evidence)
        if self.llm_provider and self._setting("reflectionUseLlmResponse", False):
            prompt = f"""
Você é o Reflection Engine da Athena.
Responda com base somente nas evidências do Athena Core.
Não invente fatos.
Diferencie conhecimento, crença e hipótese.
Se faltar dado, diga que ainda não sabe.

Pergunta do usuário:
{user_input}

Evidências:
{json.dumps(evidence, ensure_ascii=False, indent=2)}
""".strip()
            result = self.llm_provider.generate(prompt)
            if result.available and result.text:
                return result.text.strip()
        return self._fallback_summary(evidence)

    def opinion(self, user_input):
        return self.respond(user_input)

    def observe_turn(self, user_message, athena_response, metadata=None, route_result=None):
        if not self._setting("reflectionEnabled", True):
            return []

        metadata = dict(metadata or {})
        if route_result:
            metadata.setdefault("route_source", route_result.get("source", ""))
            metadata.setdefault("needs_clarification", route_result.get("needs_clarification", False))

        events = self.analyze_turn(user_message, athena_response, metadata=metadata)
        saved = []
        for event in events:
            try:
                saved.append(self.store.save(event))
            except Exception as error:
                if self.logger:
                    self.logger.log("REFLECTION_STORE_ERROR", str(error))
        self._session_events.extend(saved)
        self._session_events = self._session_events[-100:]
        return events

    def analyze_turn(self, user_message, athena_response, metadata=None):
        metadata = dict(metadata or {})
        events = []
        for detector in (
            self._detect_unknown_loop,
            self._detect_wrong_target_self_feeling,
            self._detect_missing_pronoun_resolution,
            self._detect_recent_entity_resolution_failure,
            self._detect_llm_overuse,
            self._detect_tool_hallucination,
            self._detect_pending_confirmation_block,
            self._detect_slow_known_recall,
        ):
            event = detector(user_message, athena_response, metadata)
            if event:
                events.append(event)
        return events

    def recent_events(self, limit=10):
        try:
            return self.store.list_recent(limit=limit)
        except Exception:
            return list(reversed(self._session_events[-limit:]))

    def _reflection_evidence(self):
        today = datetime.now().date().isoformat()
        week_start = (datetime.now() - timedelta(days=7)).date().isoformat()
        today_memories = self._safe_memory_call("list_memories", [], created_at_prefix=today)
        week_ingestions = self._safe_memory_call("list_knowledge_ingestions", [], created_at_prefix=week_start)
        recent_reflections = self.recent_events(limit=10)
        return {
            "identity": self.identity,
            "counts": {
                "memories": self._safe_memory_call("count_memories", 0),
                "short_term_memory": self._safe_memory_call("count_short_term_memory", 0),
                "mid_term_memory": self._safe_memory_call("count_mid_term_memory", 0),
                "long_term_memory": self._safe_memory_call("count_real_long_term_memory", 0),
                "entities": self._safe_memory_call("count_entities", 0),
                "relationships": self._safe_memory_call("count_world_relationships", 0),
                "events": self._safe_memory_call("count_world_events", 0),
                "states": self._safe_memory_call("count_entity_states", 0),
                "knowledge_sources": self._safe_memory_call("count_knowledge_sources", 0),
                "beliefs": self._safe_memory_call("count_reasoning_conclusions", 0, "belief"),
                "hypotheses": self._safe_memory_call("count_reasoning_conclusions", 0, "hypothesis"),
                "reflection_events": len(recent_reflections),
            },
            "today_memories": today_memories[:20],
            "mid_term_patterns": self._safe_memory_call("list_mid_term_memory", [], include_expired=False)[:20],
            "recent_knowledge_sources": self._safe_memory_call("list_knowledge_sources", [])[:10],
            "recent_ingestions_reference_date": week_start,
            "recent_ingestions": week_ingestions[:10],
            "recent_conclusions": self._safe_memory_call("list_reasoning_conclusions", [])[:20],
            "recent_outcomes": self._safe_memory_call("list_outcomes", [], limit=10),
            "recent_reflection_events": recent_reflections,
        }

    def _fallback_summary(self, evidence):
        counts = evidence["counts"]
        recent = evidence.get("recent_reflection_events") or []
        summary = (
            "Consigo refletir parcialmente usando minha memória interna.\n"
            f"Memórias: {counts['memories']} | Entidades: {counts['entities']} | Relações: {counts['relationships']} | "
            f"Crenças: {counts['beliefs']} | Hipóteses: {counts['hypotheses']} | "
            f"Eventos de reflexão recentes: {counts['reflection_events']}."
        )
        if recent:
            first = recent[0]
            summary += (
                "\nMinha hipótese de melhoria mais recente: "
                f"{first.get('suggestion', 'revisar resposta anterior')}"
            )
        return summary

    def _local_improvement_report(self, evidence):
        recent = evidence.get("recent_reflection_events") or []
        if not recent:
            return "Revisei minhas interações recentes e não encontrei uma falha crítica registrada agora."

        first = recent[0]
        tests = first.get("suggested_tests") or []
        test_text = f" Teste sugerido: {tests[0]}" if tests else ""
        suggestion = str(first.get("suggestion", "revisar o fluxo afetado")).rstrip(".")
        return (
            f"Encontrei uma hipótese de falha: {first.get('issue_type', 'falha não classificada')}. "
            f"Módulo suspeito: {first.get('suspected_module', 'indefinido')}. "
            f"Sugestão: {suggestion}."
            f"{test_text} Essa hipótese precisa de revisão humana antes de qualquer mudança."
        )

    def _detect_unknown_loop(self, user_message, athena_response, metadata):
        route = self._route(metadata)
        intent = self._intent(metadata)
        response_norm = self._normalize(athena_response)
        fallback = "nao entendi com seguranca" in response_norm or "pode me explicar de outro jeito" in response_norm
        if route == "unknown" or intent == "unknown" or (fallback and metadata.get("needs_clarification")):
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="unknown_loop",
                severity="medium",
                suspected_module="ConversationRouter",
                explanation="A resposta caiu em fallback generico ou manteve rota desconhecida.",
                suggestion="Registrar a entrada desconhecida, explicar a ambiguidade e criar uma rota local se o padrao for recorrente.",
                suggested_tests=[
                    "Uma entrada desconhecida deve registrar a falha e a pergunta 'o que voce nao entendeu?' nao deve repetir o mesmo fallback."
                ],
            )
        return None

    def _detect_wrong_target_self_feeling(self, user_message, athena_response, metadata):
        target = str(metadata.get("target") or "").strip()
        target_norm = self._normalize(target)
        route = self._route(metadata)
        response_norm = self._normalize(athena_response)
        self_target = target_norm in {"athena", "voce", "eu"} or (
            not target_norm and route in {"identity", "self_identity"}
        )
        self_feeling = any(
            marker in response_norm
            for marker in (
                "nao sinto",
                "nao tenho sentimentos",
                "como um humano",
                "como humano",
            )
        )
        external_query = route in {"world_query", "entity_query", "question_about_user", "learning"}
        if self_feeling and external_query and not self_target:
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="wrong_target",
                severity="high",
                suspected_module="CognitiveControlEngine/TargetResolution",
                explanation="A resposta mencionou limitacoes emocionais da Athena em uma rota sobre alvo externo.",
                suggestion="Aplicar a guarda de self-feeling somente quando o alvo for Athena ou uma pergunta de identidade da propria Athena.",
                suggested_tests=[
                    "Pergunta ou aprendizado sobre entidade externa nao deve conter 'nao sinto' nem frase equivalente de self-feeling."
                ],
            )
        return None

    def _detect_missing_pronoun_resolution(self, user_message, athena_response, metadata):
        route = self._route(metadata)
        if route != "unknown":
            return None
        text_norm = f" {self._normalize(user_message)} "
        pronouns = {" ela ", " ele ", " dela ", " dele ", " nela ", " nele ", " isso ", " esse ", " essa "}
        if any(pronoun in text_norm for pronoun in pronouns):
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="missing_pronoun_resolution",
                severity="medium",
                suspected_module="ConversationContext",
                explanation="Uma frase com pronome recente caiu em unknown.",
                suggestion="Resolver pronomes usando WorkingMemory/entidades recentes antes de classificar como unknown.",
                suggested_tests=[
                    "Depois de mencionar uma entidade, uma pergunta com pronome deve preservar o alvo recente em vez de cair em unknown."
                ],
            )
        return None

    def _detect_recent_entity_resolution_failure(self, user_message, athena_response, metadata):
        route = self._route(metadata)
        recent_entities = metadata.get("recent_entities") or metadata.get("known_recent_entities") or []
        resolution_source = str(metadata.get("resolution_source") or "")
        if route == "unknown" and recent_entities:
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="recent_entity_resolution_failed",
                severity="medium",
                suspected_module="TargetResolutionEngine",
                explanation="Havia entidade recente disponivel, mas a mensagem caiu em unknown.",
                suggestion="Usar entidades recentes e fuzzy matching conservador antes do fallback generico.",
                suggested_tests=[
                    "Uma consulta com erro de digitacao de uma entidade recente deve resolver o alvo quando a similaridade for alta."
                ],
            )
        if resolution_source == "fuzzy_failed":
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="recent_entity_resolution_failed",
                severity="medium",
                suspected_module="TargetResolutionEngine",
                explanation="A resolucao fuzzy falhou e nao produziu uma pergunta de esclarecimento.",
                suggestion="Quando o fuzzy ficar incerto, perguntar a quem o usuario se refere em vez de inventar ou cair em fallback.",
                suggested_tests=[
                    "Fuzzy ambivalente deve pedir esclarecimento em vez de criar entidade nova."
                ],
            )
        return None

    def _detect_llm_overuse(self, user_message, athena_response, metadata):
        route = self._route(metadata)
        llm_calls = self._int(metadata.get("llm_calls", metadata.get("llm_call_count", 0)))
        known_recall = route in {"world_query", "entity_query", "question_about_user"} and (
            metadata.get("used_memory") or metadata.get("used_world_model")
        )
        if llm_calls > 0 and (route in self.SIMPLE_LOCAL_ROUTES or known_recall):
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="llm_overuse",
                severity="medium",
                suspected_module="CognitiveControlEngine/ConversationRouter",
                explanation="Uma rota simples ou uma consulta conhecida usou LLM sem necessidade aparente.",
                suggestion="Priorizar Memory, World Model, SelfModel, CapabilityEngine ou ToolRegistry antes de chamar LLM.",
                suggested_tests=[
                    "Rotas simples e consultas de entidade conhecida devem manter llm_calls=0."
                ],
            )
        return None

    def _detect_tool_hallucination(self, user_message, athena_response, metadata):
        if self._route(metadata) != "external_information":
            return None
        if metadata.get("tool_available") or metadata.get("used_tool"):
            return None
        response_norm = self._normalize(athena_response)
        safe_markers = (
            "nao possuo",
            "nao tenho",
            "nao consigo consultar",
            "preciso de uma ferramenta",
            "ferramenta",
            "nao estou conectada",
            "sem acesso",
        )
        if not any(marker in response_norm for marker in safe_markers):
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="tool_hallucination",
                severity="high",
                suspected_module="ToolRegistry/ExternalInformationRoute",
                explanation="Uma rota de informacao atual respondeu sem ferramenta disponivel e sem aviso de limitacao.",
                suggestion="Responder localmente que a ferramenta necessaria nao esta configurada, sem inventar fato atual.",
                suggested_tests=[
                    "Pergunta de clima/noticias/preco atual sem ferramenta configurada deve declarar a limitacao e manter llm_calls=0."
                ],
            )
        return None

    def _detect_pending_confirmation_block(self, user_message, athena_response, metadata):
        pending = metadata.get("pending_confirmation") or metadata.get("pending_before")
        if not pending:
            return None
        route = self._route(metadata)
        text_norm = self._normalize(user_message)
        yes_no = text_norm in {"sim", "nao", "não", "ok", "confirmo", "cancela", "cancelar"}
        response_norm = self._normalize(athena_response)
        blocked = route == "pending_confirmation" or "ainda preciso saber se voce autoriza" in response_norm
        if blocked and self._is_question(user_message) and not yes_no:
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="pending_confirmation_blocking_topic_switch",
                severity="medium",
                suspected_module="PendingConfirmationPolicy",
                explanation="Uma confirmacao pendente parece ter bloqueado uma pergunta clara em outro topico.",
                suggestion="Permitir responder a pergunta atual e manter a confirmacao pendente para depois.",
                suggested_tests=[
                    "Com confirmacao pendente, uma pergunta clara sobre outro assunto deve ser respondida sem consumir a pendencia."
                ],
            )
        return None

    def _detect_slow_known_recall(self, user_message, athena_response, metadata):
        route = self._route(metadata)
        if route not in {"world_query", "entity_query", "question_about_user"}:
            return None
        if not (metadata.get("used_memory") or metadata.get("used_world_model")):
            return None
        duration_ms = self._int(metadata.get("duration_ms", metadata.get("total_ms", 0)))
        threshold = self._int(self._setting("reflectionSlowRecallMs", 2500))
        if duration_ms > threshold:
            return self._event(
                user_message,
                athena_response,
                metadata,
                issue_type="slow_known_recall",
                severity="medium",
                suspected_module="WorldModelQuery/MemoryRetrieval",
                explanation="Uma consulta conhecida demorou mais do que o limite local esperado.",
                suggestion="Revisar fast path de World Model/memoria e evitar pipeline pesado em recall conhecido.",
                suggested_tests=[
                    "Consulta de entidade conhecida deve responder abaixo do limite configurado e sem LLM."
                ],
            )
        return None

    def _event(
        self,
        user_message,
        athena_response,
        metadata,
        issue_type,
        severity,
        suspected_module,
        explanation,
        suggestion,
        suggested_tests,
    ):
        return ReflectionEvent(
            source_message=str(user_message or ""),
            athena_response=str(athena_response or ""),
            route=self._route(metadata),
            intent=self._intent(metadata),
            target=str(metadata.get("target") or ""),
            issue_type=issue_type,
            severity=severity,
            suspected_module=suspected_module,
            explanation=explanation,
            suggestion=suggestion,
            suggested_tests=suggested_tests,
            requires_human_review=True,
            metadata=dict(metadata or {}),
            critic_verdict=issue_type,
            critic_confidence=0.0,
            accepted=False,
        )

    def _wants_local_report(self, user_input):
        normalized = self._normalize(user_input)
        terms = (
            "voce errou",
            "você errou",
            "errou algo",
            "precisa melhorar",
            "melhorar",
            "analise sua ultima resposta",
            "analise a ultima resposta",
            "o que voce acha que precisa",
            "o que você acha que precisa",
        )
        return any(term in normalized for term in terms)

    def _safe_memory_call(self, method_name, fallback, *args, **kwargs):
        if not self.memory or not hasattr(self.memory, method_name):
            return fallback
        try:
            return getattr(self.memory, method_name)(*args, **kwargs)
        except Exception:
            return fallback

    def _setting(self, key, default=None):
        if self.settings and hasattr(self.settings, "get"):
            return self.settings.get(key, default)
        return default

    def _route(self, metadata):
        return str((metadata or {}).get("route") or "").strip()

    def _intent(self, metadata):
        return str((metadata or {}).get("intent") or "").strip()

    def _int(self, value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _is_question(self, text):
        raw = str(text or "").strip()
        if "?" in raw:
            return True
        normalized = self._normalize(raw)
        starters = ("quem ", "o que ", "oq ", "qual ", "quais ", "como ", "por que ", "porque ")
        return normalized.startswith(starters)

    def _normalize(self, text):
        text = str(text or "").strip().lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())
