class ConversationEngine:
    """Handles natural conversation routes without turning them into knowledge."""

    def __init__(self, identity=None, llm_provider=None, context_builder=None, health_engine=None, logger=None):
        self.identity = identity or {}
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.health_engine = health_engine
        self.logger = logger

    def respond(self, user_input, route_result=None, session_context=None):
        route = (route_result or {}).get("route", "conversation")
        if route == "greeting":
            return f"Olá. Estou aqui, {self.identity.get('creator', 'Rewell')}."
        if route == "small_talk":
            return self._small_talk()
        if route == "conversation":
            return self._natural(user_input, route_result, session_context)
        return self._natural(user_input, route_result, session_context)

    def _small_talk(self):
        status = None
        if self.health_engine:
            try:
                status = self.health_engine.snapshot()
            except Exception:
                status = None
        if status and status.get("overall") == "operational":
            return "Estou bem e operacional. Obrigada por perguntar. Como você está hoje?"
        return "Estou funcional, mas ainda monitorando alguns componentes internos. Como você está?"

    def _natural(self, user_input, route_result=None, session_context=None):
        if self.llm_provider:
            try:
                context = self.context_builder.build(user_input) if self.context_builder else ""
                session = session_context.summary() if session_context else ""
                prompt = f"""
Você é Athena em modo conversacional.
Responda de forma natural, curta e honesta.
Não tente registrar conhecimento.
Não invente fatos.
Se a mensagem parecer exigir aprendizado ou ação, peça uma confirmação clara.

Contexto persistente:
{context}

Contexto recente da sessão:
{session}

Rota conversacional:
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
        llm_available = None
        if self.health_engine:
            try:
                llm_available = bool(self.health_engine.snapshot().get("llm", {}).get("available"))
            except Exception:
                llm_available = None
        if llm_available is False:
            return (
                "Minha LLM local não está disponível para interpretar isso com segurança agora. "
                "Consigo continuar conversando e consultar meu estado interno, mas para aprender conhecimento novo preciso da interpretação estrutural ativa."
            )
        return "Estou aqui. Pode me contar melhor o que você quer fazer agora?"
