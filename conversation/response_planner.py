class ResponsePlanner:
    """Turns interpreted intent into a lightweight execution plan."""

    def plan(self, interpretation):
        interpretation = interpretation or {}
        intent = interpretation.get("intent", "conversation")
        return {
            "route": self._route_for_intent(intent),
            "intent": intent,
            "target": interpretation.get("target", ""),
            "confidence": interpretation.get("confidence", 0.0),
            "should_use_llm_response": bool(interpretation.get("should_use_llm_response", False)),
            "should_learn": bool(interpretation.get("should_learn", intent == "learning")),
            "should_query_world_model": bool(interpretation.get("should_query_world_model", intent in {"world_query", "question_about_user"})),
            "should_query_self_model": bool(interpretation.get("should_query_self_model", intent in {"identity", "creator_query", "self_status"})),
            "should_use_reasoning": bool(interpretation.get("should_use_reasoning", intent == "reasoning")),
            "should_use_agency": bool(interpretation.get("should_use_agency", intent == "agency")),
            "structured_request": interpretation.get("structured_request", {}),
            "source": interpretation.get("source", "response_planner"),
            "summary": interpretation.get("summary", intent),
        }

    def _route_for_intent(self, intent):
        route_by_intent = {
            "creator_query": "identity",
            "technical_capability": "capability",
            "question_about_user": "question_about_user",
        }
        return route_by_intent.get(intent, intent if intent else "conversation")
