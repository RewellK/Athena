class MemoryAdminEngine:
    """Local admin surface for memory, sources, research and V12 readiness."""

    def __init__(
        self,
        memory=None,
        governance_engine=None,
        reflection_engine=None,
        source_manager=None,
        research_learning_engine=None,
        self_insight_engine=None,
    ):
        self.memory = memory
        self.governance_engine = governance_engine
        self.reflection_engine = reflection_engine
        self.source_manager = source_manager
        self.research_learning_engine = research_learning_engine
        self.self_insight_engine = self_insight_engine

    def respond(self, request=None, user_input=""):
        request = dict(request or {})
        operation = request.get("operation") or "memory_admin"
        if operation == "pending_memories":
            return self._pending_memories()
        if operation == "important_memories":
            return self._important_memories()
        if operation == "stale_memories":
            return self._stale_memories()
        if operation == "improvement_memories":
            return self._improvement_memories()
        if operation == "source_admin":
            return self._sources(status=request.get("status"))
        if operation == "research_admin":
            return self._research_strategies()
        if operation == "v12_readiness":
            return self._v12_readiness()
        return self._summary()

    def _summary(self):
        snapshot = self.governance_engine.snapshot() if self.governance_engine else {"counts": {}}
        counts = snapshot.get("counts", {})
        return (
            "Consigo administrar minhas memórias em modo local. "
            f"Memória curta: {counts.get('working_memory', 0)} | "
            f"fatos no World Model: {counts.get('world_model_fact', 0)} | "
            f"memórias consolidadas: {counts.get('long_term_consolidated_memory', 0)}."
        )

    def _pending_memories(self):
        pending = self.governance_engine.pending_memories(limit=8) if self.governance_engine else []
        if not pending:
            return "Ainda não tenho memórias pendentes desse tipo."
        lines = ["Memórias pendentes que encontrei:"]
        for item in pending:
            lines.append(f"- {item['memory_id']} [{item['status']}]: {item['content'][:120]}")
        return "\n".join(lines)

    def _important_memories(self):
        important = self.governance_engine.important_memories(limit=8) if self.governance_engine else []
        if not important:
            return "Ainda não tenho memórias importantes consolidadas para listar."
        lines = ["Memórias que parecem importantes:"]
        for item in important:
            lines.append(f"- {item['memory_id']} [{item['memory_type']}]: {item['content'][:120]}")
        return "\n".join(lines)

    def _stale_memories(self):
        suggestions = self.governance_engine.cleanup_suggestions() if self.governance_engine else []
        stale = [item for item in suggestions if item.get("issue_type") == "memory_stale_detected"]
        if not stale:
            return "Não encontrei memórias velhas que eu possa marcar com segurança agora."
        first = stale[0]
        return (
            f"Encontrei {first.get('count', 0)} candidato(s) de memória possivelmente vencidos. "
            "Minha política é sugerir arquivamento ou revisão humana, não apagar automaticamente."
        )

    def _improvement_memories(self):
        insights = self.self_insight_engine.list_pending(limit=8) if self.self_insight_engine else []
        if insights:
            lines = ["Sim. Encontrei insights pendentes sobre o que preciso melhorar:"]
            for item in insights:
                source = item.get("source", "local")
                insight_type = item.get("insight_type", "insight")
                content = item.get("content", "insight sem conteúdo")
                lines.append(f"- [{source}/{insight_type}] {content}")
            lines.append("Esses pontos vêm do meu SelfInsightStore/Reflection/LLMTeacher e precisam de revisão humana.")
            return "\n".join(lines)

        events = self.reflection_engine.recent_events(limit=8) if self.reflection_engine else []
        if not events:
            return "Ainda não tenho memórias de melhoria registradas."
        lines = ["Memórias de melhoria/reflexão recentes:"]
        for item in events:
            issue = item.get("issue_type", "falha")
            suggestion = item.get("suggestion", "revisar comportamento")
            lines.append(f"- {issue}: {suggestion}")
        return "\n".join(lines)

    def _sources(self, status=None):
        if not self.source_manager:
            return "Ainda não tenho SourceManager disponível para listar fontes."
        sources = self.source_manager.registry.list_sources(status=status)
        if not sources:
            if status:
                return f"Ainda não tenho fontes com status {status}."
            return "Ainda não tenho fontes cadastradas."
        lines = ["Fontes que conheço:"]
        for source in sources:
            enabled = "enabled" if source.get("enabled") else "disabled"
            lines.append(f"- {source.get('source_id')} | {source.get('domain')} | {source.get('status')} | {enabled} | {source.get('name')}")
        return "\n".join(lines)

    def _research_strategies(self):
        strategies = self.research_learning_engine.list_strategies() if self.research_learning_engine else []
        if not strategies:
            return "Ainda não tenho estratégias de pesquisa registradas."
        lines = ["Estratégias de pesquisa que conheço:"]
        for item in strategies:
            source = item.get("preferred_source") or ", ".join(item.get("candidate_sources") or []) or "sem fonte"
            lines.append(f"- {item.get('domain')} [{item.get('status')}]: fonte={source}; inputs={', '.join(item.get('required_inputs') or [])}")
        return "\n".join(lines)

    def _v12_readiness(self):
        checks = {
            "Core local-first": True,
            "Memory/WorldModel consultáveis": bool(self.memory),
            "SourceManager/EvidenceEngine": bool(self.source_manager),
            "ResearchLearning": bool(self.research_learning_engine),
            "MemoryGovernance": bool(self.governance_engine),
            "Reflection com revisão humana": bool(self.reflection_engine),
        }
        ready = all(checks.values())
        lines = ["Checklist V12 final:"]
        for name, passed in checks.items():
            lines.append(f"- {name}: {'ok' if passed else 'pendente'}")
        verdict = "parcialmente pronta para iniciar V13-pre" if ready else "ainda não pronta para V13-pre"
        lines.append(f"Conclusão local: Athena está {verdict}.")
        return "\n".join(lines)
