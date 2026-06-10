class TemporalEngine:
    """
    V11 lockdown: temporal interpretation comes from the LLM-first extraction.
    This engine only stores/compares normalized values supplied by structure.
    """

    def normalize(self, temporal_reference):
        return temporal_reference or ""

    def compare(self, first, second):
        if not first or not second:
            return "unknown"
        if first == second:
            return "same_time"
        return "before" if str(first) < str(second) else "after"
