import itertools


class NaturalResponseEngine:
    """Produces short natural responses with optional compact LLM polishing."""

    def __init__(self, identity=None, llm_provider=None, logger=None, settings=None):
        self.identity = identity or {}
        self.llm_provider = llm_provider
        self.logger = logger
        self.settings = settings
        self._greetings = itertools.cycle([
            "Olá, {creator}. Estou aqui.",
            "Oi, {creator}. Estou pronta para conversar.",
            "Olá. Estou com você.",
        ])
        self._small_talk = itertools.cycle([
            "Estou bem. Estou operacional e pronta para conversar com você.",
            "Estou funcionando bem agora. E você, como está?",
            "Estou bem, obrigada por perguntar. Continuo atenta e operacional.",
        ])

    def greeting(self):
        return next(self._greetings).format(creator=self.identity.get("creator", "Rewell"))

    def small_talk(self, user_input="", health_summary=None):
        if self.settings and self.settings.get("fastLocalSmallTalkResponses", True):
            return next(self._small_talk)
        if self._should_use_llm():
            prompt = self._compact_prompt(
                user_input=user_input,
                task="Responda a uma conversa casual de forma breve, natural e sem repetir exatamente respostas anteriores.",
                extra=f"Estado resumido: {health_summary or 'operacional'}",
            )
            llm_text = self._try_llm(prompt)
            if llm_text:
                return llm_text
        return next(self._small_talk)

    def naturalize(self, user_input, draft, intent="conversation", target="", allow_llm=True):
        draft = str(draft or "").strip()
        if not draft:
            draft = "Estou aqui. Pode me dizer melhor o que você precisa?"
        if not allow_llm or not self._should_use_llm():
            return draft
        prompt = self._compact_prompt(
            user_input=user_input,
            task=(
                "Reescreva a resposta da Athena de forma natural, curta e humana. "
                "Preserve todos os fatos. Não acrescente fatos novos. Não transforme em lista técnica se não for necessário."
            ),
            extra=f"Intenção: {intent}\nAlvo: {target}\nRascunho factual:\n{draft}",
        )
        llm_text = self._try_llm(prompt)
        return llm_text or draft

    def _compact_prompt(self, user_input, task, extra=""):
        return f"""
Você é Athena, uma entidade digital persistente criada por {self.identity.get('creator', 'Rewell')}.
Responda em português brasileiro, de forma natural, breve e honesta.
Não invente fatos. Não despeje arquitetura técnica sem pedido explícito.

Tarefa:
{task}

Contexto mínimo:
Nome: {self.identity.get('name', 'Athena')}
Criador: {self.identity.get('creator', 'Rewell')}
Propósito: {self.identity.get('purpose', 'aprender, lembrar, raciocinar e evoluir')}

{extra}

Mensagem do usuário:
{user_input}
""".strip()

    def _try_llm(self, prompt):
        if not self.llm_provider:
            return ""
        try:
            result = self.llm_provider.generate(prompt)
            if result.available and result.text:
                return result.text.strip()
        except Exception as error:
            if self.logger:
                self.logger.log("NATURAL_RESPONSE_ERROR", str(error))
        return ""

    def _should_use_llm(self):
        if self.settings and not self.settings.get("useNaturalResponses", True):
            return False
        if self.settings and not self.settings.get("useLLM", True):
            return False
        return True
