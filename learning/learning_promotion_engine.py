from datetime import datetime


class LearningPromotionEngine:
    def __init__(self, candidate_store=None, memory=None, self_insight_engine=None, module_proposal_engine=None):
        self.candidate_store = candidate_store
        self.memory = memory
        self.self_insight_engine = self_insight_engine
        self.module_proposal_engine = module_proposal_engine

    def consolidate_approved(self):
        if not self.candidate_store:
            return {"promoted": [], "skipped": []}
        promoted = []
        skipped = []
        for candidate in self.candidate_store.list(status="approved", limit=100000):
            if candidate.get("risk_level") == "high":
                skipped.append({"candidate": candidate, "reason": "risco alto exige revisão explícita adicional"})
                continue
            destination = candidate.get("suggested_destination") or self._destination(candidate)
            result = self._promote(candidate, destination)
            if result.get("promoted"):
                updated = self.candidate_store.update_status(candidate.get("id"), "promoted")
                promoted.append({"candidate": updated or candidate, "destination": destination})
            else:
                skipped.append({"candidate": candidate, "reason": result.get("reason", "destino indisponível")})
        return {"promoted": promoted, "skipped": skipped}

    def _promote(self, candidate, destination):
        content = str(candidate.get("content") or "").strip()
        if not content:
            return {"promoted": False, "reason": "conteúdo vazio"}
        if destination in {"project_knowledge", "user_profile", "memory_governance", "command_palette", "learning_workbench"}:
            if not self.memory:
                return {"promoted": False, "reason": "MemoryDB indisponível"}
            self.memory.save_long_term_memory(
                f"[{candidate.get('candidate_type')}] {content}",
                source="supervised_learning_session",
                importance_score=80,
                metadata=self._metadata(candidate, destination),
            )
            return {"promoted": True}
        if destination == "module_proposal_engine":
            if not self.module_proposal_engine:
                return {"promoted": False, "reason": "ModuleProposalEngine indisponível"}
            proposal = self.module_proposal_engine.register({
                "title": self._proposal_title(content),
                "domain": "athena_architecture",
                "reason": content,
                "gap_type": "supervised_learning_candidate",
                "required_sources": ["human approved learning candidate"],
                "required_inputs": ["architecture discussion"],
                "risks": ["escopo incompleto", "aprovação sem desenho técnico"],
                "suggested_tests": ["Proposta criada por candidato aprovado deve continuar sem implementação automática."],
                "documentation_needed": ["docs/MODULE_PROPOSAL_ENGINE.md"],
                "acceptance_criteria": ["aprovação humana", "testes específicos", "sem automodificação"],
            })
            return {"promoted": bool(proposal)}
        return {"promoted": False, "reason": f"destino {destination} ainda não tem promoção implementada"}

    def _metadata(self, candidate, destination):
        metadata = dict(candidate.get("metadata") or {})
        return {
            "origin": self._origin(candidate),
            "created_at": candidate.get("created_at"),
            "promoted_at": datetime.now().isoformat(timespec="seconds"),
            "candidate_type": candidate.get("candidate_type"),
            "confidence": candidate.get("confidence"),
            "session_id": candidate.get("session_id"),
            "approved_by": "user",
            "original_text": candidate.get("source_excerpt") or candidate.get("content"),
            "original_candidate_id": candidate.get("id"),
            "destination": destination,
            "status": "confirmed/promoted",
            "source": "llm_teacher" if metadata.get("llm_teacher") else "local_heuristic",
            "used_llm_teacher": bool(metadata.get("llm_teacher")),
            "local_heuristic": bool(metadata.get("local_heuristic", True)),
            "risk_level": candidate.get("risk_level"),
        }

    def _origin(self, candidate):
        source = str(candidate.get("source") or "").strip()
        if source in {"", "learning_session"}:
            return "supervised_learning_session"
        return source

    def _destination(self, candidate):
        mapping = {
            "architecture_rule": "project_knowledge",
            "project_principle": "project_knowledge",
            "user_preference": "user_profile",
            "memory_policy": "memory_governance",
            "command_pattern": "command_palette",
            "training_example": "learning_workbench",
            "module_proposal": "module_proposal_engine",
        }
        return mapping.get(candidate.get("candidate_type"), "project_knowledge")

    def _proposal_title(self, content):
        words = [word.strip(".,:;!?") for word in str(content or "").split() if word.strip(".,:;!?")]
        title_words = [word for word in words if word[:1].isupper() or word.endswith("Engine") or word.endswith("Connector")]
        if title_words:
            return title_words[0].strip(".,:;!?")
        return "SupervisedLearningModuleProposal"
