import json


class MemoryInterpreter:
    """
    V8.2: LLM-first interpretation for memory relevance.
    The fallback is intentionally non-semantic and does not classify domains.
    """

    def __init__(self, llm_provider=None, context_builder=None, logger=None):
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger

    def interpret(self, text):
        llm_suggestion = self._llm_interpret(text)
        if llm_suggestion:
            return self._normalize_llm_suggestion(llm_suggestion)
        return self._minimal_fallback(text)

    def _minimal_fallback(self, text):
        clean = text.strip()
        is_question = clean.endswith("?")
        is_short = len(clean) < 20
        score = 0 if not is_short and not is_question else -10
        return {
            "importance_score": score,
            "emotional_score": 0,
            "relationship_score": 0,
            "identity_score": 0,
            "future_score": 0,
            "categories": [],
            "temporary": True,
            "important": False,
            "needs_confirmation": False,
            "suggested_layer": "ignore" if score <= 0 else "short",
            "reason": "LLM indisponível; fallback não semântico usado para evitar adivinhação.",
        }

    def _llm_interpret(self, text):
        if not self.llm_provider:
            return None

        prompt = (
            "Você é uma região cognitiva da Athena. A Athena Core é dona da memória.\n"
            "Classifique a relevância da mensagem sem gravar nada.\n"
            "Não use listas fixas de domínios. Interprete semanticamente.\n"
            "Responda somente JSON com campos: importance_score, emotional_score, relationship_score, identity_score, future_score, "
            "categories, temporary, important, needs_confirmation, suggested_layer, reason.\n\n"
            f"Mensagem: {text}"
        )

        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None

            raw = result.text.strip()
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end >= start:
                return json.loads(raw[start:end + 1])
            return None
        except Exception as error:
            if self.logger:
                self.logger.log("MEMORY_INTERPRETER_ERROR", f"Falha ao interpretar memória com LLM: {error}")
            return None

    def _normalize_llm_suggestion(self, suggestion):
        try:
            score = int(float(suggestion.get("importance_score", 0)))
        except (TypeError, ValueError):
            score = 0
        categories = suggestion.get("categories", [])
        if not isinstance(categories, list):
            categories = [str(categories)]
        return {
            "importance_score": score,
            "emotional_score": self._score(suggestion.get("emotional_score", 0)),
            "relationship_score": self._score(suggestion.get("relationship_score", 0)),
            "identity_score": self._score(suggestion.get("identity_score", 0)),
            "future_score": self._score(suggestion.get("future_score", 0)),
            "categories": categories,
            "temporary": bool(suggestion.get("temporary", score < 30)),
            "important": bool(suggestion.get("important", score >= 50)),
            "needs_confirmation": bool(suggestion.get("needs_confirmation", 25 <= score < 50)),
            "suggested_layer": self._normalize_layer(suggestion.get("suggested_layer"), score),
            "reason": str(suggestion.get("reason", "interpretação sem justificativa")),
        }

    def _score(self, value):
        try:
            score = int(float(value))
        except (TypeError, ValueError):
            score = 0
        return max(0, min(100, score))

    def _normalize_layer(self, value, score):
        layer = str(value or "").strip()
        if layer in {"short", "mid", "long_candidate", "long_confirm", "long", "ignore"}:
            return "long_candidate" if layer == "long" else layer
        if score >= 90:
            return "long_candidate"
        if score >= 75:
            return "long_candidate"
        if score >= 50:
            return "mid"
        if score >= 20:
            return "short"
        return "ignore"
