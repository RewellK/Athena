from dataclasses import dataclass


@dataclass
class LearningDecision:
    action: str
    category: str
    score: int
    reason: str
    should_save: bool = False
    payload: dict = None


class LearningEngine:
    """
    V11: legacy direct learning rules are locked down.
    Learning decisions should be made from structural extraction and confidence,
    not from keywords or phrase lists.
    """

    def __init__(self, memory, creator_name="Rewell"):
        self.memory = memory
        self.creator_name = creator_name

    def evaluate_structure(self, extraction, decision):
        score = int(float(decision.get("confidence", 0.0)) * 100)
        action = decision.get("decision", "ask_context")
        return LearningDecision(
            action=action,
            category="structural_knowledge",
            score=score,
            reason=decision.get("reason", "decisão baseada em confiança estrutural"),
            should_save=action == "save",
            payload={"extraction": extraction},
        )

    def evaluate(self, text):
        return LearningDecision(
            action="delegate_to_structural_pipeline",
            category="unclassified",
            score=0,
            reason="Na V11, texto livre deve passar por IntentionEngine e KnowledgeExtractionEngine.",
            should_save=False,
            payload={"text": text},
        )

    def apply(self, decision):
        return "Aprendizado direto desativado. Use o pipeline estrutural da Athena."
