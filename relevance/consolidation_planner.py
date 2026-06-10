class ConsolidationPlanner:
    """Plans memory and World Model consolidation from structured signals."""

    PRIORITIES = {"ignore", "short", "mid", "long_candidate", "long_confirm"}

    def plan(
        self,
        resolved_intent=None,
        resolved_target=None,
        extracted_knowledge=None,
        relevance=None,
        current_memory_state=None,
        current_world_model_state=None,
    ):
        intent = resolved_intent if isinstance(resolved_intent, dict) else {}
        extraction = extracted_knowledge if isinstance(extracted_knowledge, dict) else {}
        relevance = relevance if isinstance(relevance, dict) else {}
        priority = self._priority(relevance.get("memory_priority"), relevance.get("relevance_score", 0))
        score = self._score(relevance.get("relevance_score", relevance.get("importance_score", 0)))
        has_knowledge = self._has_structures(extraction)

        store_short = priority in {"short", "mid", "long_candidate", "long_confirm"} or score >= 20
        store_mid = priority in {"mid", "long_candidate", "long_confirm"} or score >= 50
        store_candidate = priority in {"long_candidate", "long_confirm"} or score >= 75
        require_confirmation = priority == "long_confirm" or bool(relevance.get("confirmation_required", False))
        update_world_model = has_knowledge and bool(intent.get("should_learn", intent.get("intent") == "learning"))

        return {
            "store_short_term": bool(store_short),
            "store_mid_term": bool(store_mid),
            "store_long_term_candidate": bool(store_candidate),
            "require_confirmation": bool(require_confirmation),
            "update_world_model": bool(update_world_model),
            "ask_follow_up": bool(relevance.get("should_ask_follow_up", False)),
            "follow_up_question": str(relevance.get("follow_up_question") or ""),
            "reason": self._reason(priority, score, has_knowledge, update_world_model),
        }

    def _has_structures(self, extraction):
        for key in ("entities", "relationships", "events", "states"):
            value = extraction.get(key)
            if isinstance(value, list) and value:
                return True
        return False

    def _priority(self, value, score):
        priority = str(value or "").strip()
        if priority in self.PRIORITIES:
            return priority
        score = self._score(score)
        if score >= 90:
            return "long_candidate"
        if score >= 75:
            return "long_candidate"
        if score >= 50:
            return "mid"
        if score >= 20:
            return "short"
        return "ignore"

    def _score(self, value):
        try:
            number = int(round(float(value)))
        except (TypeError, ValueError):
            number = 0
        return max(0, min(100, number))

    def _reason(self, priority, score, has_knowledge, update_world_model):
        world_text = "com atualização estrutural" if update_world_model else "sem atualização estrutural"
        knowledge_text = "há estruturas extraídas" if has_knowledge else "não há estruturas extraídas"
        return f"prioridade={priority}, score={score}, {knowledge_text}, {world_text}"
