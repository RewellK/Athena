from dataclasses import asdict, dataclass, field


@dataclass
class ResearchPlan:
    domain: str
    required_inputs: list = field(default_factory=list)
    evidence_required: bool = True
    freshness_ttl_seconds: int = 3600
    risks: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class ResearchPlanner:
    """Local research planner. It records procedure, not factual answers."""

    DEFAULT_PLANS = {
        "weather": ResearchPlan(
            domain="weather",
            required_inputs=["location", "date"],
            freshness_ttl_seconds=1800,
            risks=["stale_forecast", "missing_location"],
        ),
        "vehicles": ResearchPlan(
            domain="vehicles",
            required_inputs=["model", "year", "version_optional", "location_optional"],
            freshness_ttl_seconds=86400,
            risks=["unvalidated_source", "scraping_policy", "price_variation"],
        ),
        "news": ResearchPlan(
            domain="news",
            required_inputs=["topic_optional", "date_range"],
            freshness_ttl_seconds=900,
            risks=["stale_news", "editorial_bias", "missing_source"],
        ),
        "finance": ResearchPlan(
            domain="finance",
            required_inputs=["asset", "date_or_now"],
            freshness_ttl_seconds=300,
            risks=["market_delay", "missing_source"],
        ),
    }

    def plan(self, domain):
        domain = str(domain or "unknown_external")
        plan = self.DEFAULT_PLANS.get(domain)
        if plan:
            return plan.to_dict()
        return ResearchPlan(
            domain=domain,
            required_inputs=["query", "validated_source"],
            freshness_ttl_seconds=3600,
            risks=["missing_source", "unclear_domain"],
        ).to_dict()
