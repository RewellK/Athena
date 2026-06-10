import json


class FollowUpQuestionEngine:
    """Generates contextual follow-up questions from structured relevance."""

    def __init__(self, llm_provider=None, identity=None, logger=None, settings=None):
        self.llm_provider = llm_provider
        self.identity = identity or {}
        self.logger = logger
        self.settings = settings

    def generate(self, user_message, relevance, extracted_knowledge=None, resolved_target=None, recent_context=""):
        relevance = relevance if isinstance(relevance, dict) else {}
        if not relevance.get("should_ask_follow_up", False):
            return ""

        existing = str(relevance.get("follow_up_question") or "").strip()
        if existing:
            return existing

        if self._should_use_llm():
            prompt = self._build_prompt(user_message, relevance, extracted_knowledge, resolved_target, recent_context)
            try:
                result = self.llm_provider.generate(prompt)
                if result.available and result.text:
                    question = result.text.strip()
                    if question:
                        return question
            except Exception as error:
                if self.logger:
                    self.logger.log("FOLLOW_UP_ERROR", str(error))

        target = self._best_target(resolved_target, relevance)
        if target:
            return f"Quer me contar mais sobre {target}?"
        return "Quer que eu trate isso como algo importante para lembrar com cuidado?"

    def _build_prompt(self, user_message, relevance, extracted_knowledge, resolved_target, recent_context):
        return f"""
Você é o Follow-up Question Engine da Athena.
Gere uma única pergunta curta, contextual e útil.
Não responda pelo usuário.
Não finja sentimentos humanos.
Não use pergunta genérica se houver alvo, relação ou lacuna contextual clara.
Não use markdown.

Identidade:
- Athena: {self.identity.get("name", "Athena")}
- Criador/usuário principal: {self.identity.get("creator", "Rewell")}

Mensagem do usuário:
{user_message}

Alvo resolvido:
{json.dumps(resolved_target or {}, ensure_ascii=False)}

Relevância:
{json.dumps(relevance, ensure_ascii=False, indent=2)}

Conhecimento extraído:
{json.dumps(extracted_knowledge or {}, ensure_ascii=False, indent=2)}

Contexto recente:
{recent_context}
""".strip()

    def _best_target(self, resolved_target, relevance):
        if isinstance(resolved_target, dict):
            target = str(resolved_target.get("target") or "").strip()
            if target:
                return target
        entities = relevance.get("related_entities") if isinstance(relevance.get("related_entities"), list) else []
        for entity in entities:
            text = str(entity or "").strip()
            if text:
                return text
        return ""

    def _should_use_llm(self):
        if not self.llm_provider:
            return False
        if self.settings and not self.settings.get("useLLM", True):
            return False
        return True
