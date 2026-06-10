from conversation.intent_interpreter import IntentInterpreter
from conversation.response_planner import ResponsePlanner


class ConversationRouter:
    """Conversation-first router for V12.3.

    It does not extract knowledge. It delegates interpretation to IntentInterpreter
    and converts the result into a generic route plan.
    """

    VALID_ROUTES = {
        "greeting",
        "small_talk",
        "identity",
        "capability",
        "technical_capability",
        "question_about_user",
        "self_status",
        "memory_query",
        "world_query",
        "reasoning",
        "learning",
        "agency",
        "system",
        "error_query",
        "conversation",
        "unknown",
    }

    def __init__(self, llm_provider=None, context_builder=None, logger=None, identity=None, settings=None):
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger
        self.identity = identity or {}
        self.settings = settings
        self.intent_interpreter = IntentInterpreter(llm_provider, self.identity, logger, settings)
        self.response_planner = ResponsePlanner()

    def route(self, user_input, session_context=None, pending_state=None):
        interpretation = self.intent_interpreter.interpret(user_input, session_context, pending_state)
        plan = self.response_planner.plan(interpretation)
        route = plan.get("route", "conversation")
        if route not in self.VALID_ROUTES:
            route = "unknown"
        structured_request = plan.get("structured_request") if isinstance(plan.get("structured_request"), dict) else {}
        return {
            "route": route,
            "intent": plan.get("intent", route),
            "target": plan.get("target", ""),
            "summary": plan.get("summary", route),
            "confidence": self._confidence(plan.get("confidence"), 0.0),
            "needs_clarification": self._confidence(plan.get("confidence"), 0.0) < 0.45,
            "should_learn": bool(plan.get("should_learn", route == "learning")),
            "should_use_llm_response": bool(plan.get("should_use_llm_response", False)),
            "should_query_world_model": bool(plan.get("should_query_world_model", route in {"world_query", "question_about_user"})),
            "should_query_self_model": bool(plan.get("should_query_self_model", route in {"identity", "self_status"})),
            "should_use_reasoning": bool(plan.get("should_use_reasoning", route == "reasoning")),
            "should_use_agency": bool(plan.get("should_use_agency", route == "agency")),
            "structured_request": structured_request,
            "source": plan.get("source", "conversation_router"),
            "intent_interpretation_ms": interpretation.get("duration_ms", 0) if isinstance(interpretation, dict) else 0,
        }

    def _confidence(self, value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))
