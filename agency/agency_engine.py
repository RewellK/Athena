class AgencyEngine:
    """
    Coordinates intention -> goal -> plan -> proposed action.
    It does not interpret user language directly; it receives structured intention.
    """

    def __init__(self, memory, goal_engine, action_engine, logger=None):
        self.memory = memory
        self.goal_engine = goal_engine
        self.action_engine = action_engine
        self.logger = logger

    def consider(self, intention_id, intention):
        goal = self.goal_engine.propose_goal(intention_id, intention)
        if not goal:
            return None
        plan = self.action_engine.plan_for_goal(goal)
        if not plan:
            return {
                "goal": goal,
                "plan": None,
                "message": "Formei um objetivo, mas ainda não consegui propor um plano seguro."
            }
        return {"goal": goal, "plan": plan, "message": self._format_proposal(goal, plan)}

    def approve_plan(self, plan_id):
        return self.action_engine.execute_approved_plan(plan_id)

    def reject_plan(self, plan_id):
        return self.action_engine.reject_plan(plan_id)

    def _format_proposal(self, goal, plan):
        lines = [
            "Tenho uma intenção que pode virar ação, mas preciso da sua autorização antes.",
            f"Objetivo proposto: {goal['description']}",
            f"Motivo: {goal.get('rationale', '')}",
            f"Plano: {plan.get('plan_summary', '')}",
            "Ações propostas:"
        ]
        for step in plan.get("steps", []):
            lines.append(f"- {step['description']} | ferramenta: {step['tool_id']} | razão: {step.get('reason', '')}")
        lines.append("Você autoriza esse plano?")
        return "\n".join(lines)
