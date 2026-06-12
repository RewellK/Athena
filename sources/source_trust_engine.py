class SourceTrustEngine:
    TRUST_LEVELS = {
        "official": 0.95,
        "high": 0.85,
        "medium": 0.65,
        "low": 0.35,
        "unverified": 0.10,
        "user_provided": 0.45,
        "llm_generated": 0.05,
    }

    def score(self, trust_level):
        return self.TRUST_LEVELS.get(str(trust_level or "unverified").strip().lower(), 0.10)

    def can_support_factual_answer(self, source):
        source = source or {}
        if source.get("status") != "enabled":
            return False
        if not source.get("enabled"):
            return False
        if source.get("validation_status") != "passed":
            return False
        return self.score(source.get("trust_level")) >= self.TRUST_LEVELS["medium"]
