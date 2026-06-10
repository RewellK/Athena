class TargetResolutionEngine:
    """
    Validates the target returned by the LLM intent resolver.

    It does not parse natural language. It only normalizes the already-structured
    target so Athena Core can choose a safe subsystem.
    """

    VALID_TARGET_TYPES = {"self", "user", "entity", "world", "tool", "unknown"}

    def resolve(self, intent_result):
        data = intent_result if isinstance(intent_result, dict) else {}
        target_type = self._clean_label(data.get("target_type"))
        if target_type not in self.VALID_TARGET_TYPES:
            target_type = "unknown"
        return {
            "target": str(data.get("target") or "").strip(),
            "target_type": target_type,
            "confidence": self._confidence(data.get("confidence"), 0.0),
            "source": data.get("source", "target_resolution"),
        }

    def _clean_label(self, value):
        clean = str(value or "").strip().lower()
        chars = []
        for char in clean:
            if char.isalnum() or char in {"_", "-"}:
                chars.append(char)
            else:
                chars.append("_")
        label = "".join(chars)
        while "__" in label:
            label = label.replace("__", "_")
        return label.strip("_")

    def _confidence(self, value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))
