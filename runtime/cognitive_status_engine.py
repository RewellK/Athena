class CognitiveStatusEngine:
    def __init__(
        self,
        runtime_supervisor=None,
        task_registry=None,
        learning_session_engine=None,
        learning_candidate_store=None,
        self_insight_engine=None,
        module_proposal_engine=None,
        day_memory_buffer=None,
    ):
        self.runtime_supervisor = runtime_supervisor
        self.task_registry = task_registry
        self.learning_session_engine = learning_session_engine
        self.learning_candidate_store = learning_candidate_store
        self.self_insight_engine = self_insight_engine
        self.module_proposal_engine = module_proposal_engine
        self.day_memory_buffer = day_memory_buffer

    def respond(self, operation="status"):
        if operation == "diagnostic":
            return self.diagnostic()
        return self.status()

    def status(self):
        runtime = self.runtime_supervisor.get_status() if self.runtime_supervisor else {"state": "offline"}
        task_counts = self.task_registry.counts() if self.task_registry else {}
        active_session = self.learning_session_engine.active_session() if self.learning_session_engine else None
        candidates = self.learning_candidate_store.count(status="candidate") if self.learning_candidate_store else 0
        approved = self.learning_candidate_store.count(status="approved") if self.learning_candidate_store else 0
        insights = len(self.self_insight_engine.list_pending(limit=100)) if self.self_insight_engine else 0
        proposals = 0
        if self.module_proposal_engine:
            proposals = len(self.module_proposal_engine.list_proposals(status="pending_human_review"))
        state = runtime.get("state", "offline")
        if state in {"offline", "stopped"}:
            runtime_label = "offline"
        else:
            runtime_label = "pausada" if runtime.get("paused") else "ativa"
        safe_mode = "sim" if runtime.get("safe_mode") else "não"
        session_text = "nenhuma sessão de aprendizagem ativa"
        if active_session:
            session_text = f"sessão de aprendizagem ativa ({active_session.get('scope')})"
        return (
            f"Estou com runtime {runtime_label}, estado {state}. "
            f"Modo seguro: {safe_mode}. "
            f"Tenho {candidates} aprendizado(s) candidato(s), {approved} aprovado(s) aguardando consolidação, "
            f"{insights} insight(s) pendente(s) e {proposals} proposta(s) de módulo pendente(s). "
            f"Tarefas: {task_counts or {'pending': 0}}. "
            f"Agora: {session_text}."
        )

    def diagnostic(self):
        runtime = self.runtime_supervisor.get_status() if self.runtime_supervisor else {"state": "offline"}
        task_counts = self.task_registry.counts() if self.task_registry else {}
        buffer_summary = self.day_memory_buffer.summary() if self.day_memory_buffer else {"entries": 0}
        lines = [
            "Diagnóstico local do runtime:",
            f"- Estado: {runtime.get('state', 'offline')}",
            f"- Heartbeat: {runtime.get('last_heartbeat_at') or 'nenhum'}",
            f"- Último erro: {runtime.get('last_error') or 'nenhum'}",
            f"- Modo seguro: {runtime.get('safe_mode')}",
            f"- Pausado: {runtime.get('paused')}",
            f"- Tarefas: {task_counts or {'pending': 0}}",
            f"- Buffer diário: {buffer_summary.get('entries', 0)} entrada(s), status {buffer_summary.get('status', 'open')}",
        ]
        return "\n".join(lines)
