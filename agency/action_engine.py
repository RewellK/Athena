from agency.json_utils import parse_json_object, clamp, ensure_list


class ActionEngine:
    """Transforms agency goals into plans, proposed actions and outcomes."""

    def __init__(self, memory, tool_registry, llm_provider=None, context_builder=None, logger=None):
        self.memory = memory
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger

    def plan_for_goal(self, goal):
        if not self.llm_provider:
            return None
        tools = self.tool_registry.list_available()
        prompt = self._build_plan_prompt(goal, tools)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            plan = self._normalize_plan(parse_json_object(result.text), tools)
            if not plan.get("steps"):
                return None
            plan_id = self.memory.save_plan(goal["id"], plan, status="proposed", requires_approval=True)
            plan["id"] = plan_id
            for step in plan["steps"]:
                self.memory.save_action(
                    plan_id,
                    step.get("tool_id"),
                    step.get("description"),
                    status="awaiting_approval",
                    approval_required=True,
                )
            return plan
        except Exception as error:
            if self.logger:
                self.logger.log("ACTION_ENGINE_PLAN_ERROR", str(error))
            return None

    def execute_approved_plan(self, plan_id):
        actions = self.memory.list_actions(status="awaiting_approval")
        executed = []
        for action in actions:
            action_id, row_plan_id, tool_id, description, status, approval_required, result_summary, created_at, executed_at = action
            if row_plan_id != plan_id:
                continue
            summary = "Ação aprovada registrada. Execução externa permanece controlada nesta versão."
            self.memory.update_action_status(action_id, "approved", summary, executed=True)
            self.memory.mark_tool_used(tool_id, success=True)
            self.memory.save_outcome(action_id, "approved", summary, "A V11 registrou aprovação humana antes de ação permanente.")
            executed.append(description)
        return executed

    def reject_plan(self, plan_id):
        actions = self.memory.list_actions(status="awaiting_approval")
        rejected = []
        for action in actions:
            action_id, row_plan_id, tool_id, description, status, approval_required, result_summary, created_at, executed_at = action
            if row_plan_id != plan_id:
                continue
            self.memory.update_action_status(action_id, "rejected", "Usuário rejeitou o plano.", executed=False)
            self.memory.save_outcome(action_id, "rejected", "Plano rejeitado pelo usuário.", "A Athena manteve aprovação humana como limite de agência.")
            rejected.append(description)
        return rejected

    def _build_plan_prompt(self, goal, tools):
        context = self.context_builder.build("") if self.context_builder else ""
        return f"""
Você é o Action Engine da Athena.

Transforme um objetivo em plano e ações propostas.
Você NÃO deve executar ações.
Você NÃO deve assumir aprovação humana.
Você deve escolher ferramentas por capacidade, confiança, custo, latência e sucesso histórico.
Não use regras por domínio.
Retorne SOMENTE JSON válido.

Schema:
{{
  "plan_summary": "string",
  "requires_human_approval": true,
  "confidence": 0.0,
  "steps": [
    {{
      "description": "string",
      "tool_id": "string",
      "reason": "string"
    }}
  ]
}}

Contexto persistente:
{context}

Objetivo:
{goal}

Ferramentas disponíveis:
{tools}
""".strip()

    def _normalize_plan(self, parsed, tools):
        if not isinstance(parsed, dict):
            return {"steps": []}
        tool_ids = {tool["id"] for tool in tools}
        steps = []
        for item in ensure_list(parsed.get("steps")):
            if not isinstance(item, dict):
                continue
            description = str(item.get("description") or "").strip()
            tool_id = str(item.get("tool_id") or "").strip()
            if not description or tool_id not in tool_ids:
                continue
            steps.append({
                "description": description,
                "tool_id": tool_id,
                "reason": str(item.get("reason") or "").strip(),
            })
        return {
            "plan_summary": str(parsed.get("plan_summary") or "").strip(),
            "requires_human_approval": True,
            "confidence": clamp(parsed.get("confidence"), 0.5),
            "steps": steps,
        }
