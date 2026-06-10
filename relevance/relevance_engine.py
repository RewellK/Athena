import json
import time

from relevance.emotional_relevance_engine import EmotionalRelevanceEngine
from relevance.relationship_relevance_engine import RelationshipRelevanceEngine


class RelevanceEngine:
    """
    LLM-first human relevance evaluator.

    The LLM interprets human meaning. Athena Core receives a bounded JSON
    structure and decides what to persist. No natural-language phrase is used as
    a rule in this class.
    """

    VALID_PRIORITIES = {"ignore", "short", "mid", "long_candidate", "long_confirm"}

    def __init__(self, llm_provider=None, identity=None, logger=None, settings=None):
        self.llm_provider = llm_provider
        self.identity = identity or {}
        self.logger = logger
        self.settings = settings
        self.emotional = EmotionalRelevanceEngine()
        self.relationship = RelationshipRelevanceEngine()

    def evaluate(
        self,
        user_message,
        resolved_intent=None,
        resolved_target=None,
        recent_context="",
        extracted_knowledge=None,
        known_entities=None,
        current_user_identity=None,
        self_identity=None,
    ):
        started_at = time.perf_counter()
        resolved_intent = resolved_intent if isinstance(resolved_intent, dict) else {}
        resolved_target = resolved_target if isinstance(resolved_target, dict) else {}
        extraction = extracted_knowledge if isinstance(extracted_knowledge, dict) else {}
        known_entities = known_entities if isinstance(known_entities, list) else []

        parsed = None
        if self._should_use_llm():
            prompt = self._build_prompt(
                user_message=user_message,
                resolved_intent=resolved_intent,
                resolved_target=resolved_target,
                recent_context=recent_context,
                extracted_knowledge=extraction,
                known_entities=known_entities,
                current_user_identity=current_user_identity,
                self_identity=self_identity,
            )
            parsed = self._llm_evaluate(prompt)

        result = self._normalize(
            parsed,
            fallback_context={
                "intent": resolved_intent,
                "target": resolved_target,
                "extraction": extraction,
                "message": user_message,
            },
        )
        result["duration_ms"] = int((time.perf_counter() - started_at) * 1000)
        return result

    def _build_prompt(
        self,
        user_message,
        resolved_intent,
        resolved_target,
        recent_context,
        extracted_knowledge,
        known_entities,
        current_user_identity,
        self_identity,
    ):
        creator = self.identity.get("creator", "Rewell")
        athena = self.identity.get("name", "Athena")
        return f"""
Você é o RelevanceEngine da Athena.
Retorne SOMENTE JSON válido, sem markdown e sem explicação fora do JSON.
Não responda ao usuário.
Não grave memória.
Não invente fatos.

Princípio arquitetural:
- A LLM interpreta linguagem natural.
- Athena Core decide persistência, World Model, raciocínio, ferramentas e resposta final.
- Relevância humana não é a mesma coisa que recorrência.
- Uma informação dita uma única vez pode ser central se afetar identidade, relações, futuro, cuidado ou significado humano.
- Não classifique uma fala longa e humanamente importante como saudação apenas porque contém cumprimento.
- Não finja sentimentos humanos da Athena.

Identidade mínima:
- Athena: {athena}
- Usuário/criador principal: {creator}

Escalas:
- 0 a 20: baixa importância ou ruído de conversa.
- 20 a 50: contexto útil, mas não central.
- 50 a 75: informação relacional, autobiográfica ou recorrente.
- 75 a 90: informação muito importante para vida, relação, objetivo ou futuro.
- 90 a 100: informação central para identidade, vínculo, afeto, futuro ou memória de longo prazo.

Prioridades permitidas:
ignore, short, mid, long_candidate, long_confirm

Schema obrigatório:
{{
  "relevance_score": 0,
  "emotional_score": 0,
  "relationship_score": 0,
  "identity_score": 0,
  "future_score": 0,
  "memory_priority": "ignore|short|mid|long_candidate|long_confirm",
  "should_ask_follow_up": false,
  "follow_up_question": "",
  "reason": "",
  "risks": []
}}

Intenção resolvida:
{json.dumps(resolved_intent, ensure_ascii=False, indent=2)}

Alvo resolvido:
{json.dumps(resolved_target, ensure_ascii=False, indent=2)}

Conhecimento extraído, se houver:
{json.dumps(extracted_knowledge or {}, ensure_ascii=False, indent=2)}

Entidades conhecidas relevantes:
{json.dumps(known_entities, ensure_ascii=False, indent=2)}

Identidade do usuário, se disponível:
{json.dumps(current_user_identity or {}, ensure_ascii=False, indent=2)}

Self identity, se disponível:
{json.dumps(self_identity or {}, ensure_ascii=False, indent=2)}

Contexto recente:
{recent_context}

Mensagem do usuário:
{user_message}
""".strip()

    def _llm_evaluate(self, prompt):
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            return self._parse_json(result.text)
        except Exception as error:
            if self.logger:
                self.logger.log("RELEVANCE_ENGINE_ERROR", str(error))
            return None

    def _parse_json(self, raw_text):
        raw = str(raw_text or "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _normalize(self, parsed, fallback_context=None):
        if not isinstance(parsed, dict):
            return self._fallback(fallback_context or {})

        scores = self.emotional.normalize_scores(parsed)
        priority = str(parsed.get("memory_priority") or "").strip()
        if priority not in self.VALID_PRIORITIES:
            priority = self._priority_from_score(scores["relevance_score"])

        risks = parsed.get("risks")
        if not isinstance(risks, list):
            risks = []

        signals = self.relationship.structured_signals((fallback_context or {}).get("extraction"))
        result = {
            **scores,
            "importance_score": scores["relevance_score"],
            "memory_priority": priority,
            "should_ask_follow_up": bool(parsed.get("should_ask_follow_up", False)),
            "follow_up_question": str(parsed.get("follow_up_question") or "").strip(),
            "reason": str(parsed.get("reason") or "sem justificativa da LLM").strip(),
            "risks": [str(item) for item in risks],
            "related_entities": signals["related_entities"],
            "relationship_count": signals["relationship_count"],
            "state_count": signals["state_count"],
            "event_count": signals["event_count"],
            "source": "llm_relevance",
        }
        result["confirmation_required"] = priority == "long_confirm"
        return result

    def _fallback(self, context):
        intent = context.get("intent") if isinstance(context.get("intent"), dict) else {}
        extraction = context.get("extraction") if isinstance(context.get("extraction"), dict) else {}
        signals = self.relationship.structured_signals(extraction)
        score = 0
        if signals["has_structured_knowledge"]:
            score = 40
        if signals["relationship_count"] > 0:
            score = max(score, 55)
        if intent.get("intent") == "learning" or intent.get("should_learn"):
            score = max(score, 35)
        priority = self._priority_from_score(score)
        return {
            "relevance_score": score,
            "importance_score": score,
            "emotional_score": 0,
            "relationship_score": 45 if signals["relationship_count"] else 0,
            "identity_score": 0,
            "future_score": 0,
            "memory_priority": priority,
            "should_ask_follow_up": False,
            "follow_up_question": "",
            "reason": "LLM indisponível; fallback estrutural conservador usado sem interpretar linguagem natural.",
            "risks": ["llm_unavailable"],
            "related_entities": signals["related_entities"],
            "relationship_count": signals["relationship_count"],
            "state_count": signals["state_count"],
            "event_count": signals["event_count"],
            "confirmation_required": priority == "long_confirm",
            "source": "structured_relevance_fallback",
        }

    def _priority_from_score(self, score):
        score = self.emotional._score(score)
        if score >= 90:
            return "long_candidate"
        if score >= 75:
            return "long_candidate"
        if score >= 50:
            return "mid"
        if score >= 20:
            return "short"
        return "ignore"

    def _should_use_llm(self):
        if not self.llm_provider:
            return False
        if self.settings and not self.settings.get("useLLM", True):
            return False
        return True
