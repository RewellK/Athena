from research.research_planner import ResearchPlanner
from research.research_result_evaluator import ResearchResultEvaluator
from research.research_strategy_memory import ResearchStrategy, ResearchStrategyMemory


class ResearchLearningEngine:
    """Learns reusable research procedures from source outcomes.

    The engine does not fetch facts and does not ask an LLM by itself. If an LLM
    suggests a strategy, that suggestion is stored as a candidate requiring
    human review.
    """

    def __init__(self, memory=None, planner=None, evaluator=None):
        self.memory = memory or ResearchStrategyMemory()
        self.planner = planner or ResearchPlanner()
        self.evaluator = evaluator or ResearchResultEvaluator()

    def observe_missing_source(self, domain, proposal=None, learned_from="source_discovery"):
        proposal = dict(proposal or {})
        plan = self.planner.plan(domain)
        return self.memory.upsert(ResearchStrategy(
            domain=plan["domain"],
            candidate_sources=[proposal.get("name")] if proposal.get("name") else [],
            required_inputs=plan["required_inputs"],
            evidence_required=plan["evidence_required"],
            freshness_ttl_seconds=plan["freshness_ttl_seconds"],
            learned_from=learned_from,
            confidence=0.45,
            status="needs_source",
            requires_human_review=True,
            notes=proposal.get("reason", ""),
        ))

    def observe_capability_gap(self, domain, gap=None, module_proposal=None):
        gap = dict(gap or {})
        module_proposal = dict(module_proposal or {})
        plan = self.planner.plan(domain)
        status = "needs_source" if gap.get("gap_type") == "missing_source" else "needs_module"
        return self.memory.upsert(ResearchStrategy(
            domain=plan["domain"],
            candidate_sources=[module_proposal.get("related_source_candidate")] if module_proposal.get("related_source_candidate") else [],
            required_inputs=module_proposal.get("required_inputs") or plan["required_inputs"],
            evidence_required=True,
            freshness_ttl_seconds=plan["freshness_ttl_seconds"],
            learned_from="capability_gap",
            confidence=0.4,
            status=status,
            requires_human_review=True,
            notes=module_proposal.get("reason") or gap.get("reason", ""),
        ))

    def observe_external_result(self, domain, source=None, result=None, status="completed"):
        source = dict(source or {})
        result = dict(result or {})
        evidence = dict(result.get("evidence") or {})
        plan = self.planner.plan(domain)
        evaluation = self.evaluator.evaluate(status, evidence=evidence, source=source)
        previous = self.memory.get_active(plan["domain"])
        confidence = float(previous.get("confidence", 0.55)) if previous else 0.55
        confidence = max(0.0, min(1.0, confidence + evaluation.get("confidence_delta", 0.0)))
        success_count = int(previous.get("success_count", 0)) if previous else 0
        failure_count = int(previous.get("failure_count", 0)) if previous else 0
        if evaluation["outcome"] == "success":
            success_count += 1
        elif evaluation["outcome"] == "failure":
            failure_count += 1

        return self.memory.upsert(ResearchStrategy(
            domain=plan["domain"],
            preferred_source=source.get("source_id", ""),
            required_inputs=plan["required_inputs"],
            evidence_required=plan["evidence_required"],
            freshness_ttl_seconds=int(source.get("freshness_ttl_seconds") or plan["freshness_ttl_seconds"]),
            learned_from="external_research_result",
            confidence=confidence,
            status=evaluation["status"],
            requires_human_review=False,
            success_count=success_count,
            failure_count=failure_count,
            notes=f"Resultado observado: {evaluation['outcome']}",
        ))

    def learn_from_llm_suggestion(self, domain, suggestion, candidate_sources=None):
        plan = self.planner.plan(domain)
        return self.memory.upsert(ResearchStrategy(
            domain=plan["domain"],
            candidate_sources=list(candidate_sources or []),
            required_inputs=plan["required_inputs"],
            evidence_required=plan["evidence_required"],
            freshness_ttl_seconds=plan["freshness_ttl_seconds"],
            learned_from="llm_strategy_suggestion",
            confidence=0.35,
            status="candidate",
            requires_human_review=True,
            notes=str(suggestion or "").strip(),
        ))

    def list_strategies(self, domain=None, status=None):
        return self.memory.list(domain=domain, status=status)

    def active_strategy_for(self, domain):
        return self.memory.get_active(domain)
