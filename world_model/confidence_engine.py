class ConfidenceEngine:

    AUTO_SAVE_THRESHOLD = 0.90
    CONFIRMATION_THRESHOLD = 0.60

    def normalize(self, value, default=0.70):
        if value is None:
            return default
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        if numeric > 1:
            numeric = numeric / 100
        return max(0.0, min(1.0, numeric))

    def evaluate_extraction(self, extraction):
        confidences = []
        for key in ["entities", "relationships", "events", "states", "temporal_references"]:
            for item in extraction.get(key, []):
                confidences.append(self.normalize(item.get("confidence"), extraction.get("confidence", 0.70)))
        if not confidences:
            return {
                "decision": "ignore",
                "confidence": 0.0,
                "reason": "nenhuma estrutura confiável foi encontrada"
            }
        minimum = min(confidences)
        average = sum(confidences) / len(confidences)
        if minimum >= self.AUTO_SAVE_THRESHOLD:
            return {"decision": "save", "confidence": average, "reason": "todas as estruturas possuem alta confiança"}
        if minimum >= self.CONFIRMATION_THRESHOLD:
            return {"decision": "confirm", "confidence": average, "reason": "há estruturas plausíveis, mas a Athena deve confirmar antes de salvar"}
        return {"decision": "ask_context", "confidence": average, "reason": "a extração tem baixa confiança e precisa de mais contexto"}

    def requires_confirmation(self, extraction):
        return self.evaluate_extraction(extraction)["decision"] == "confirm"
