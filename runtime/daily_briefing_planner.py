class DailyBriefingPlanner:
    def __init__(
        self,
        runtime_supervisor=None,
        learning_candidate_store=None,
        self_insight_engine=None,
        module_proposal_engine=None,
        source_manager=None,
    ):
        self.runtime_supervisor = runtime_supervisor
        self.learning_candidate_store = learning_candidate_store
        self.self_insight_engine = self_insight_engine
        self.module_proposal_engine = module_proposal_engine
        self.source_manager = source_manager

    def prepare(self):
        status = self.runtime_supervisor.get_status() if self.runtime_supervisor else {"state": "offline"}
        learning_pending = self.learning_candidate_store.count(status="candidate") if self.learning_candidate_store else 0
        insights_pending = len(self.self_insight_engine.list_pending(limit=100)) if self.self_insight_engine else 0
        proposals_pending = 0
        if self.module_proposal_engine:
            proposals_pending = len(self.module_proposal_engine.list_proposals(status="pending_human_review"))
        return {
            "runtime": status,
            "learning_candidates_pending": learning_pending,
            "self_insights_pending": insights_pending,
            "module_proposals_pending": proposals_pending,
            "calendar": "Ainda não tenho integração de calendário validada.",
        }

    def render(self):
        briefing = self.prepare()
        runtime = briefing.get("runtime") or {}
        lines = [
            "Briefing cognitivo local:",
            f"- Runtime: {runtime.get('state', 'offline')}.",
            f"- Aprendizados aguardando revisão: {briefing.get('learning_candidates_pending', 0)}.",
            f"- SelfInsights pendentes: {briefing.get('self_insights_pending', 0)}.",
            f"- Propostas de módulo pendentes: {briefing.get('module_proposals_pending', 0)}.",
            f"- Calendário: {briefing.get('calendar')}",
        ]
        return "\n".join(lines)
