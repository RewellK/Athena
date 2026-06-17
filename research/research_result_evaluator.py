class ResearchResultEvaluator:
    """Evaluates whether a research attempt should strengthen a strategy."""

    def evaluate(self, status, evidence=None, source=None):
        source = dict(source or {})
        evidence = dict(evidence or {})
        if status == "completed" and evidence.get("evidence_id"):
            return {
                "outcome": "success",
                "confidence_delta": 0.05,
                "status": "active",
                "source_id": source.get("source_id", ""),
            }
        if status == "missing_source":
            return {"outcome": "needs_source", "confidence_delta": 0.0, "status": "needs_source"}
        if status in {"source_not_validated", "source_candidate", "pending_validation"}:
            return {"outcome": "needs_validation", "confidence_delta": 0.0, "status": "needs_validation"}
        return {
            "outcome": "failure",
            "confidence_delta": -0.05,
            "status": "failed",
            "source_id": source.get("source_id", ""),
        }
