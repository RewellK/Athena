class EmotionalRelevanceEngine:
    """Normalizes emotional and identity salience from relevance JSON.

    The semantic judgment comes from the LLM. This class keeps the numeric
    contract stable for MemoryManager, consolidation and debug surfaces.
    """

    def normalize_scores(self, result):
        data = result if isinstance(result, dict) else {}
        return {
            "relevance_score": self._score(data.get("relevance_score", data.get("importance_score", 0))),
            "emotional_score": self._score(data.get("emotional_score", 0)),
            "relationship_score": self._score(data.get("relationship_score", 0)),
            "identity_score": self._score(data.get("identity_score", 0)),
            "future_score": self._score(data.get("future_score", 0)),
        }

    def should_preserve(self, result):
        scores = self.normalize_scores(result)
        return max(
            scores["relevance_score"],
            scores["emotional_score"],
            scores["relationship_score"],
            scores["identity_score"],
            scores["future_score"],
        ) >= 50

    def _score(self, value):
        try:
            number = int(round(float(value)))
        except (TypeError, ValueError):
            number = 0
        return max(0, min(100, number))
