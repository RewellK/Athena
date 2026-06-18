from commands.command_interpreter import CommandInterpreter
from commands.command_mode_registry import CommandModeRegistry
from commands.command_session import CommandSessionStore


class CommandPaletteEngine:
    def __init__(
        self,
        interpreter=None,
        mode_registry=None,
        session_store=None,
        learning_session_engine=None,
        learning_harvest_worker=None,
        learning_report_engine=None,
        learning_candidate_store=None,
        learning_promotion_engine=None,
        cognitive_status_engine=None,
        runtime_supervisor=None,
        study_command_engine=None,
        memory=None,
    ):
        self.interpreter = interpreter or CommandInterpreter()
        self.mode_registry = mode_registry or CommandModeRegistry()
        self.session_store = session_store or CommandSessionStore()
        self.learning_session_engine = learning_session_engine
        self.learning_harvest_worker = learning_harvest_worker
        self.learning_report_engine = learning_report_engine
        self.learning_candidate_store = learning_candidate_store
        self.learning_promotion_engine = learning_promotion_engine
        self.cognitive_status_engine = cognitive_status_engine
        self.runtime_supervisor = runtime_supervisor
        self.study_command_engine = study_command_engine
        self.memory = memory

    def interpret(self, text):
        return self.interpreter.interpret(text)

    def respond(self, user_input="", command=None):
        command = dict(command or self.interpret(user_input))
        name = command.get("command")
        if not name:
            return "Não reconheci esse comando cognitivo ainda."
        handler = getattr(self, f"_handle_{name}", None)
        if not handler:
            return "Reconheci a intenção de comando, mas esse modo ainda está documentado como futuro."
        return handler(command)

    def _handle_start_learning(self, command):
        if not self.learning_session_engine:
            return "Ainda não tenho LearningSessionEngine conectado."
        session = self.learning_session_engine.start(scope="current_conversation")
        self.session_store.start("aprendizagem", scope=session.get("scope"), policy={"requires_review": True})
        if self.runtime_supervisor:
            self.runtime_supervisor.start(background=False)
        return (
            "Modo de aprendizado iniciado. Eu não vou guardar tudo. "
            "Vou estudar o que acontecer, separar o que parece importante e te mostrar antes de consolidar."
        )

    def _handle_stop_learning(self, command):
        session = self.learning_session_engine.stop() if self.learning_session_engine else None
        self.session_store.end("aprendizagem")
        count = self.learning_candidate_store.count(status="candidate") if self.learning_candidate_store else 0
        if not session:
            return "Não havia modo aprendizagem ativo."
        return (
            f"Modo aprendizagem encerrado. Separei {count} candidato(s) aguardando revisão. "
            "Nada foi consolidado automaticamente."
        )

    def _handle_learning_status(self, command):
        session = self.learning_session_engine.active_session() if self.learning_session_engine else None
        count = self.learning_candidate_store.count(status="candidate") if self.learning_candidate_store else 0
        if not session:
            return f"Modo aprendizagem não está ativo. Tenho {count} candidato(s) pendente(s) de revisão."
        return (
            f"Modo aprendizagem está ativo desde {session.get('started_at')}. "
            f"Separei {count} candidato(s) até agora. Nada foi consolidado ainda."
        )

    def _handle_learning_report(self, command):
        if self.learning_harvest_worker:
            self.learning_harvest_worker.harvest_active_session()
        if not self.learning_report_engine:
            return "Ainda não tenho LearningReportEngine conectado."
        session = self.learning_session_engine.active_session() if self.learning_session_engine else None
        session_id = session.get("id") if session else None
        return self.learning_report_engine.render(title="Relatório do modo aprendizagem", session_id=session_id)

    def _handle_approve_learning(self, command):
        return self._update_candidates(command, "approved", "aprovado")

    def _handle_reject_learning(self, command):
        return self._update_candidates(command, "rejected", "rejeitado")

    def _handle_edit_learning(self, command):
        if not self.learning_candidate_store:
            return "Ainda não tenho LearningCandidateStore conectado."
        identifiers = command.get("identifiers") or []
        if not identifiers:
            return "Preciso saber qual candidato você quer editar."
        updated = self.learning_candidate_store.edit(identifiers[0], command.get("content", ""))
        if not updated:
            return "Não encontrei esse candidato de aprendizado para editar."
        return "Aprendizado atualizado. Ele continua aguardando aprovação humana."

    def _handle_consolidate_approved(self, command):
        if not self.learning_promotion_engine:
            return "Ainda não tenho LearningPromotionEngine conectado."
        result = self.learning_promotion_engine.consolidate_approved()
        promoted = result.get("promoted") or []
        skipped = result.get("skipped") or []
        return (
            f"Consolidei {len(promoted)} candidato(s) aprovado(s) nos destinos disponíveis. "
            f"Pulei {len(skipped)} item(ns) por política ou destino indisponível."
        )

    def _handle_discard_rejected(self, command):
        if not self.learning_candidate_store:
            return "Ainda não tenho LearningCandidateStore conectado."
        rejected = self.learning_candidate_store.list(status="rejected", limit=100000)
        for candidate in rejected:
            self.learning_candidate_store.update_status(candidate.get("id"), "discarded")
        return f"Descartei {len(rejected)} candidato(s) rejeitado(s)."

    def _handle_study_day(self, command):
        if not self.study_command_engine:
            return "Ainda não tenho StudyCommandEngine conectado."
        return self.study_command_engine.study()

    def _handle_study_report(self, command):
        if not self.study_command_engine:
            return "Ainda não tenho StudyCommandEngine conectado."
        return self.study_command_engine.report()

    def _handle_runtime_status(self, command):
        if self.cognitive_status_engine:
            return self.cognitive_status_engine.status()
        return "Ainda não tenho CognitiveStatusEngine conectado."

    def _handle_diagnostic(self, command):
        if self.cognitive_status_engine:
            return self.cognitive_status_engine.diagnostic()
        return "Ainda não tenho diagnóstico runtime conectado."

    def _handle_start_runtime(self, command):
        if not self.runtime_supervisor:
            return "Ainda não tenho RuntimeSupervisor conectado."
        status = self.runtime_supervisor.start(background=False)
        return f"Runtime iniciado. Estado atual: {status.get('state')}."

    def _handle_silence(self, command):
        if self.runtime_supervisor:
            self.runtime_supervisor.pause(reason="silence_mode")
        self.session_store.start("silencio", scope="runtime", policy={"suppress_notifications": True})
        return "Modo silêncio ativado. Continuo respondendo quando você me chamar, mas reduzi processos e notificações não essenciais."

    def _handle_resume_runtime(self, command):
        if self.runtime_supervisor:
            self.runtime_supervisor.resume(reason="resume_from_silence")
        self.session_store.end("silencio")
        return "Retomei os processos internos leves."

    def _handle_stop_runtime(self, command):
        if not self.runtime_supervisor:
            return "Ainda não tenho RuntimeSupervisor conectado."
        result = self.runtime_supervisor.stop(reason="command_palette_shutdown")
        return f"Runtime encerrado com segurança. Estado final: {result.get('status')}."

    def _handle_learned_about_topic(self, command):
        topic = str(command.get("topic") or "").strip()
        if not topic:
            return "Preciso saber o tema que você quer consultar."
        if not self.memory:
            return "Ainda não tenho MemoryDB conectado para consultar aprendizados consolidados."
        normalized_topic = self._normalize(topic)
        matches = []
        try:
            if hasattr(self.memory, "list_long_term_memory_with_metadata"):
                rows = self.memory.list_long_term_memory_with_metadata()
            else:
                rows = [(*row, {}) for row in self.memory.list_long_term_memory()]
        except Exception:
            rows = []
        for _id, content, source, _importance, _created_at, metadata in rows:
            normalized_content = self._normalize(content)
            if self._topic_matches(normalized_topic, normalized_content):
                matches.append({"content": str(content or ""), "source": source, "metadata": dict(metadata or {})})
        if not matches:
            return f"Ainda não tenho aprendizado consolidado sobre {topic}. Posso ter candidatos aguardando revisão."
        clean = [item["content"].split("] ", 1)[-1] for item in matches[:4]]
        origins = {item["metadata"].get("origin") or item["source"] for item in matches[:4]}
        origin_text = ""
        if origins:
            origin_text = " Origem: " + ", ".join(sorted(origin for origin in origins if origin)) + "."
        return "Sobre " + topic + ", eu aprendi localmente que " + " ".join(clean) + origin_text

    def _handle_list_commands(self, command):
        modes = self.mode_registry.list_modes()
        lines = ["Comandos cognitivos disponíveis agora:"]
        for mode in modes:
            status = "ativo" if mode.get("implemented") else "futuro"
            lines.append(f"- {mode.get('name')}: {mode.get('description')} ({status})")
        return "\n".join(lines)

    def _update_candidates(self, command, status, label):
        if not self.learning_candidate_store:
            return "Ainda não tenho LearningCandidateStore conectado."
        identifiers = command.get("identifiers") or []
        if not identifiers:
            return "Preciso saber quais candidatos você quer atualizar."
        updated = []
        for identifier in identifiers:
            candidate = self.learning_candidate_store.update_status(identifier, status)
            if candidate:
                updated.append(candidate)
        if not updated:
            return "Não encontrei esses candidatos de aprendizado."
        return f"Aprendizado(s) {', '.join(str(item.get('id'))[:8] for item in updated)} {label}(s)."

    def _normalize(self, text):
        replacements = {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }
        normalized = str(text or "").strip().lower()
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return " ".join(normalized.split())

    def _topic_matches(self, normalized_topic, normalized_content):
        if normalized_topic in normalized_content:
            return True
        topic_words = [word for word in normalized_topic.split() if len(word) > 3]
        if topic_words and any(word in normalized_content for word in topic_words):
            return True
        semantic_groups = [
            {"memoria", "memorias", "conversa", "conversas", "diaria", "diarias", "dia", "buffer", "temporario", "temporaria", "permanente"},
            {"aprendizado", "aprender", "estudar", "candidato", "candidatos", "consolidar"},
        ]
        topic_set = set(topic_words)
        content_set = set(normalized_content.split())
        for group in semantic_groups:
            if topic_set & group and content_set & group:
                return True
        return False
