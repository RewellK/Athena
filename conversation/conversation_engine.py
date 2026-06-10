from conversation.natural_response_engine import NaturalResponseEngine


class ConversationEngine:
    """Handles conversational routes before any learning attempt."""

    def __init__(self, identity=None, llm_provider=None, context_builder=None, health_engine=None, logger=None, settings=None):
        self.identity = identity or {}
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.health_engine = health_engine
        self.logger = logger
        self.settings = settings
        self.natural = NaturalResponseEngine(identity, llm_provider, logger, settings)

    def respond(self, user_input, route_result=None, session_context=None):
        route = (route_result or {}).get("route", "conversation")
        if route == "greeting":
            return self.natural.greeting()
        if route == "small_talk":
            return self.natural.small_talk(user_input, self._health_summary())
        if route == "conversation":
            return self._natural(user_input, route_result, session_context)
        return self._natural(user_input, route_result, session_context)

    def _natural(self, user_input, route_result=None, session_context=None):
        if self.llm_provider and self.settings and self.settings.get("useNaturalResponses", True):
            try:
                recent = session_context.summary(limit=6) if session_context else ""
                prompt = f"""
Você é Athena em modo conversacional.
Responda de forma natural, curta e honesta.
Não tente registrar conhecimento.
Não invente fatos.
Se a mensagem exigir aprendizado, confirmação ou ação, peça uma confirmação clara.

Identidade:
Nome: {self.identity.get('name', 'Athena')}
Criador: {self.identity.get('creator', 'Rewell')}
Propósito: {self.identity.get('purpose', 'aprender, lembrar, raciocinar e evoluir')}

Contexto recente:
{recent}

Rota planejada:
{route_result}

Mensagem:
{user_input}
""".strip()
                result = self.llm_provider.generate(prompt)
                if result.available and result.text:
                    return result.text.strip()
            except Exception as error:
                if self.logger:
                    self.logger.log("CONVERSATION_ENGINE_ERROR", str(error))
        return "Estou aqui. Pode me dizer melhor o que você quer fazer agora?"

    def _health_summary(self):
        if not self.health_engine:
            return "operacional"
        try:
            snapshot = self.health_engine.snapshot()
            return snapshot.get("overall", "operacional")
        except Exception:
            return "estado interno parcialmente desconhecido"
