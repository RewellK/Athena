import unicodedata

from learning.learning_candidate_store import LearningCandidate


DEFAULT_RISK_LEXICON = {
    "high": [
        "senha",
        "senhas",
        "token",
        "tokens",
        "chave",
        "credencial",
        "credenciais",
        "cpf",
        "cartao",
        "banco",
        "medico",
        "juridico",
        "localizacao",
    ],
    "medium": [
        "familia",
        "rotina",
        "financeiro",
        "terceiro",
        "terceiros",
        "endereco",
        "relacionamento",
        "privado",
        "pessoal",
    ],
}


class LearningHarvestWorker:
    def __init__(self, session_engine=None, candidate_store=None, teacher_loop=None, risk_lexicon=None):
        self.session_engine = session_engine
        self.candidate_store = candidate_store
        self.teacher_loop = teacher_loop
        self.risk_lexicon = self._normalize_lexicon(risk_lexicon or DEFAULT_RISK_LEXICON)

    def run_once(self):
        return self.harvest_active_session()

    def harvest_active_session(self):
        if not self.session_engine or not self.candidate_store:
            return {"status": "missing_learning_organs", "created": 0}
        session = self.session_engine.active_session()
        if not session:
            return {"status": "no_active_session", "created": 0}
        messages = self.session_engine.unprocessed_messages(session.get("id"))
        created = self.harvest_messages(session, messages)
        self.session_engine.mark_messages_processed(session.get("id"), count=len(messages))
        self.session_engine.update_counts()
        return {"status": "completed", "created": len(created)}

    def harvest_entries(self, session_id, entries, source="daily_review"):
        fake_session = {"id": session_id, "scope": source, "use_llm_teacher": False}
        messages = [
            {"role": entry.get("source", "user"), "content": entry.get("content", ""), "metadata": entry}
            for entry in entries
        ]
        return self.harvest_messages(fake_session, messages, source=source)

    def harvest_messages(self, session, messages, source="learning_session"):
        created = []
        for message in messages or []:
            if str(message.get("role")) not in {"user", "conversation"}:
                continue
            content = str(message.get("content") or "").strip()
            if self._is_noise(content):
                continue
            candidate = self._candidate_from_text(session, content, source=source)
            if candidate:
                created.append(self.candidate_store.save(candidate))

        if session.get("use_llm_teacher") and self.teacher_loop:
            try:
                for message in messages or []:
                    if str(message.get("role")) == "user":
                        self.teacher_loop.enqueue_turn(message.get("content", ""), "", metadata={"source": source})
            except Exception:
                pass
        return created

    def _candidate_from_text(self, session, content, source="learning_session"):
        words = self._words(content)
        if len(words) < 4:
            return None
        normalized = " ".join(words)
        risk = self._risk_level(normalized)
        candidate_type, destination, reason = self._classify(normalized)
        if not candidate_type:
            return None
        return LearningCandidate(
            session_id=session.get("id", ""),
            candidate_type=candidate_type,
            content=content,
            reason=reason,
            confidence=0.62 if risk == "low" else 0.50,
            source_excerpt=content[:240],
            suggested_destination=destination,
            risk_level=risk,
            status="candidate" if risk != "high" else "candidate",
            requires_human_review=True,
            source=source,
            metadata={"scope": session.get("scope", ""), "local_heuristic": True},
        )

    def _classify(self, normalized):
        word_set = set(normalized.split())
        if self._matches_lexicon(normalized, "high"):
            return "safety_boundary", "memory_governance", "contém material sensível e exige política explícita."
        if "nao deve" in normalized or "não deve" in normalized:
            return "safety_boundary", "memory_governance", "define um limite ou regra negativa de segurança."
        if "athena" in word_set and word_set & {"deve", "precisa", "necessita"}:
            return "architecture_rule", "project_knowledge", "define uma regra arquitetural sobre a Athena."
        if word_set & {"orgao", "orgaos", "órgão", "órgãos", "engine", "connector", "modulo", "módulo"}:
            return "module_proposal", "module_proposal_engine", "sugere um órgão ou módulo futuro."
        if word_set & {"comando", "modo", "palheta"}:
            return "command_pattern", "command_palette", "descreve padrão de comando ou modo cognitivo."
        if word_set & {"prefiro", "preferencia", "preferência"} or "eu quero" in normalized:
            return "user_preference", "user_profile", "parece uma preferência explícita do usuário."
        if word_set & {"memoria", "memória", "guardar", "salvar", "consolidar"}:
            return "memory_policy", "memory_governance", "descreve política ou destino de memória."
        if word_set & {"aprender", "aprendizado", "treino", "estudar"}:
            return "training_example", "learning_workbench", "pode virar exemplo de aprendizado supervisionado."
        return "project_principle", "project_knowledge", "parece um princípio ou decisão de projeto discutida."

    def _risk_level(self, normalized):
        if self._matches_lexicon(normalized, "high"):
            return "high"
        if self._matches_lexicon(normalized, "medium"):
            return "medium"
        return "low"

    def _matches_lexicon(self, normalized, level):
        terms = self.risk_lexicon.get(level, set())
        words = set(normalized.split())
        for term in terms:
            if " " in term and term in normalized:
                return True
            if term in words:
                return True
        return False

    def _normalize_lexicon(self, lexicon):
        normalized = {}
        source = lexicon if isinstance(lexicon, dict) else {}
        for level in ("high", "medium"):
            values = source.get(level) or DEFAULT_RISK_LEXICON.get(level, [])
            normalized[level] = {self._normalize(value) for value in values if str(value or "").strip()}
        return normalized

    def _is_noise(self, content):
        normalized = self._normalize(content)
        words = normalized.split()
        if not normalized or len(words) < 3:
            return True
        question_openers = {"quem", "que", "qual", "quais", "quando", "onde", "como", "porque", "quanto", "quantos", "quantas"}
        if words[0] in question_openers or (words[0] == "athena" and len(words) > 1 and words[1] in question_openers):
            return True
        if "?" in str(content or ""):
            return True
        word_set = set(words)
        if "status" in word_set and word_set & {"athena", "voce", "vc"}:
            return True
        command_starts = (
            "athena aprender",
            "athena comando",
            "athena status",
            "athena relatorio",
            "aprovar",
            "rejeitar",
            "editar",
            "consolidar",
        )
        return normalized.startswith(command_starts)

    def _words(self, text):
        normalized = self._normalize(text)
        chars = []
        for char in normalized:
            chars.append(char if char.isalnum() else " ")
        return "".join(chars).split()

    def _normalize(self, text):
        normalized = unicodedata.normalize("NFKD", str(text or "").strip().lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return " ".join(normalized.split())
