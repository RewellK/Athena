from conversation.intent_resolution_engine import IntentResolutionEngine


class IntentInterpreter(IntentResolutionEngine):
    """Deprecated compatibility wrapper.

    V12.4 moved conversational interpretation to IntentResolutionEngine.
    This class remains only so older imports do not break. It contains no local
    linguistic rules and delegates to the LLM-first resolver.
    """

    def interpret(self, user_input, session_context=None, pending_state=None):
        return self.resolve(user_input, session_context=session_context, pending_state=pending_state)
