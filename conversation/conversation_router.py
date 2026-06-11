from conversation.intent_resolution_engine import IntentResolutionEngine
from conversation.response_planner import ResponsePlanner
from conversation.target_resolution_engine import TargetResolutionEngine
from relevance.relevance_engine import RelevanceEngine


class ConversationRouter:
    """LLM-guided conversation router for V12.4.

    The router does not understand language through keyword rules. It asks the
    IntentResolutionEngine for a compact structure, validates the target, and
    returns a plan for Athena Core to execute.
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
        "external_information",
        "conversation",
        "unknown",
    }

    def __init__(self, llm_provider=None, context_builder=None, logger=None, identity=None, settings=None, tool_registry=None, relevance_engine=None):
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger
        self.identity = identity or {}
        self.settings = settings
        self.intent_resolution_engine = IntentResolutionEngine(llm_provider, self.identity, logger, settings, tool_registry=tool_registry)
        self.target_resolution_engine = TargetResolutionEngine()
        self.response_planner = ResponsePlanner()
        self.relevance_engine = relevance_engine or RelevanceEngine(llm_provider, self.identity, logger, settings)

    def route(self, user_input, session_context=None, pending_state=None):
        resolution = self.intent_resolution_engine.resolve(user_input, session_context, pending_state)
        target = self.target_resolution_engine.resolve(resolution)
        if not resolution.get("available", True):
            return self._unavailable_route(resolution)

        interpretation = dict(resolution)
        interpretation.update({
            "target": target.get("target"),
            "target_type": target.get("target_type"),
        })
        plan = self.response_planner.plan(interpretation)
        plan = self._apply_query_precedence(user_input, plan)
        relevance = self._evaluate_relevance(user_input, plan, target, session_context)
        original_route = plan.get("route", "conversation")
        plan = self._apply_relevance(user_input, plan, relevance)
        route = plan.get("route", "conversation")
        if route not in self.VALID_ROUTES:
            route = "unknown"
        structured_request = plan.get("structured_request") if isinstance(plan.get("structured_request"), dict) else {}
        return {
            "route": route,
            "intent": plan.get("intent", route),
            "target": plan.get("target", ""),
            "target_type": plan.get("target_type", target.get("target_type", "unknown")),
            "summary": plan.get("summary", route),
            "confidence": self._confidence(plan.get("confidence"), 0.0),
            "needs_clarification": self._confidence(plan.get("confidence"), 0.0) < 0.45,
            "requires_memory": bool(plan.get("requires_memory", False)),
            "requires_tool": bool(plan.get("requires_tool", False)),
            "tool_name": plan.get("tool_name"),
            "should_learn": bool(plan.get("should_learn", route == "learning")),
            "should_use_llm_response": bool(plan.get("should_use_llm_response", False)),
            "should_query_world_model": bool(plan.get("should_query_world_model", route in {"world_query", "question_about_user"})),
            "should_query_self_model": bool(plan.get("should_query_self_model", route in {"identity", "self_status"})),
            "should_use_reasoning": bool(plan.get("should_use_reasoning", route == "reasoning")),
            "should_use_agency": bool(plan.get("should_use_agency", route == "agency")),
            "structured_request": structured_request,
            "relevance": relevance,
            "original_route": original_route,
            "source": plan.get("source", "conversation_router"),
            "intent_interpretation_ms": resolution.get("duration_ms", 0) if isinstance(resolution, dict) else 0,
        }

    def _unavailable_route(self, resolution):
        return {
            "route": "unknown",
            "intent": "unknown",
            "target": "",
            "target_type": "unknown",
            "summary": "intent_resolution_unavailable",
            "confidence": 0.0,
            "needs_clarification": True,
            "requires_memory": False,
            "requires_tool": False,
            "tool_name": None,
            "should_learn": False,
            "should_use_llm_response": False,
            "should_query_world_model": False,
            "should_query_self_model": False,
            "should_use_reasoning": False,
            "should_use_agency": False,
            "structured_request": {"error": resolution.get("error", "LLM indisponível")},
            "source": "llm_intent_unavailable",
            "intent_interpretation_ms": resolution.get("duration_ms", 0),
        }

    def _confidence(self, value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))

    def _evaluate_relevance(self, user_input, plan, target, session_context):
        route = plan.get("route")
        if route in {"external_information", "system", "capability", "technical_capability", "self_status", "error_query"}:
            return {}
        if not self.relevance_engine:
            return {}
        recent = session_context.summary(limit=6) if session_context else ""
        try:
            return self.relevance_engine.evaluate(
                user_message=user_input,
                resolved_intent=plan,
                resolved_target=target,
                recent_context=recent,
                self_identity=self.identity,
            )
        except Exception as error:
            if self.logger:
                self.logger.log("ROUTER_RELEVANCE_ERROR", str(error))
            return {}

    def _apply_query_precedence(self, user_input, plan):
        if not self._looks_like_explicit_query(user_input):
            return plan
        route = plan.get("route")
        if route in {"world_query", "question_about_user", "memory_query", "identity", "reasoning", "external_information", "system"}:
            return plan
        target = str(plan.get("target") or "").strip()
        target_type = str(plan.get("target_type") or "unknown")
        if not target:
            return plan
        if target_type == "entity":
            return self._query_plan(plan, route="world_query", intent="entity_query")
        if target_type == "user":
            return self._query_plan(plan, route="question_about_user", intent="user_identity")
        if target_type == "world":
            return self._query_plan(plan, route="world_query", intent="world_query")
        return plan

    def _query_plan(self, plan, route, intent):
        adjusted = dict(plan)
        adjusted.update({
            "route": route,
            "intent": intent,
            "requires_memory": True,
            "should_learn": False,
            "should_query_world_model": route in {"world_query", "question_about_user"},
            "summary": "explicit_query",
            "source": f"{plan.get('source', 'conversation_router')}+query_precedence",
        })
        return adjusted

    def _apply_relevance(self, user_input, plan, relevance):
        if not isinstance(relevance, dict) or not relevance:
            return plan
        route = plan.get("route")
        if route in {"world_query", "question_about_user", "memory_query"}:
            return plan
        if self._looks_like_explicit_query(user_input):
            return plan
        priority = str(relevance.get("memory_priority") or "ignore")
        try:
            score = int(relevance.get("relevance_score", 0))
        except (TypeError, ValueError):
            score = 0
        if priority == "ignore" and score < 50:
            return plan
        if route in {"greeting", "small_talk", "conversation", "unknown"} or (route == "identity" and score >= 75):
            adjusted = dict(plan)
            adjusted.update({
                "route": "learning",
                "intent": "learning",
                "should_learn": True,
                "requires_memory": True,
                "summary": "high_relevance_learning",
                "source": f"{plan.get('source', 'conversation_router')}+relevance",
            })
            return adjusted
        return plan

    def _looks_like_explicit_query(self, user_input):
        text = str(user_input or "").strip()
        if not text:
            return False
        normalized = self._normalize_query_text(text)
        if "?" in text:
            return True
        question_openers = {
            "quem",
            "que",
            "qual",
            "quais",
            "quando",
            "onde",
            "como",
            "porque",
            "por que",
            "quanto",
            "quantos",
            "quantas",
        }
        return any(normalized == opener or normalized.startswith(f"{opener} ") for opener in question_openers)

    def _normalize_query_text(self, text):
        normalized = str(text or "").strip().lower()
        for source, target in {
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
        }.items():
            normalized = normalized.replace(source, target)
        return " ".join(normalized.split())
