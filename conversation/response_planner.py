class ResponsePlanner:
    """Turns LLM-resolved intent into a lightweight execution plan.

    The mapping here is structural routing, not natural-language interpretation.
    It maps canonical intent labels returned by the LLM to Athena Core modules.
    """

    def plan(self, interpretation):
        interpretation = interpretation or {}
        intent = interpretation.get("intent", "conversation")
        route = self._route_for_intent(intent)
        return {
            "route": route,
            "intent": intent,
            "target": interpretation.get("target", ""),
            "target_type": interpretation.get("target_type", "unknown"),
            "confidence": interpretation.get("confidence", 0.0),
            "requires_memory": bool(interpretation.get("requires_memory", False)),
            "requires_tool": bool(interpretation.get("requires_tool", False)),
            "tool_name": interpretation.get("tool_name"),
            "should_use_llm_response": bool(interpretation.get("should_use_llm_response", False)),
            "should_learn": bool(interpretation.get("should_learn", intent == "learning")),
            "should_query_world_model": bool(interpretation.get("requires_world_model", route in {"world_query", "question_about_user"})),
            "should_query_self_model": route in {"identity", "self_status"},
            "should_use_reasoning": bool(interpretation.get("requires_reasoning", route == "reasoning")),
            "should_use_agency": route == "agency",
            "structured_request": interpretation.get("structured_request", {}),
            "source": interpretation.get("source", "response_planner"),
            "summary": interpretation.get("summary", intent),
        }

    def _route_for_intent(self, intent):
        route_by_intent = {
            "self_identity": "identity",
            "creator_query": "identity",
            "user_identity": "question_about_user",
            "entity_query": "world_query",
            "technical_capability": "technical_capability",
            "external_information": "external_information",
        }
        return route_by_intent.get(intent, intent if intent else "conversation")
