class ToolRegistry:
    """
    Registry of action extensions.

    Tool metadata is not intelligence. It only describes capabilities so the
    Agency/Action engines can choose through reasoning instead of hardcoded
    routing.
    """

    DEFAULT_TOOLS = [
        {
            "id": "world_model_core",
            "capability": "represent structured knowledge as entities relationships events states",
            "confidence": 0.90,
            "cost": 0.05,
            "latency": 0.10,
            "success_rate": 0.80,
        },
        {
            "id": "knowledge_ingestion_core",
            "capability": "convert supervised external content into candidate knowledge",
            "confidence": 0.85,
            "cost": 0.20,
            "latency": 0.30,
            "success_rate": 0.70,
        },
        {
            "id": "reasoning_core",
            "capability": "infer beliefs hypotheses and explanations from existing evidence",
            "confidence": 0.85,
            "cost": 0.10,
            "latency": 0.20,
            "success_rate": 0.75,
        },
        {
            "id": "reflection_core",
            "capability": "reflect on outcomes learning progress and uncertainty",
            "confidence": 0.80,
            "cost": 0.10,
            "latency": 0.20,
            "success_rate": 0.75,
        },
        {
            "id": "self_code_awareness_read",
            "capability": "read local project structure and summarize operational code body",
            "confidence": 0.85,
            "cost": 0.05,
            "latency": 0.10,
            "success_rate": 0.75,
        },
        {
            "id": "git_awareness_read_only",
            "capability": "read git repository status branch history diff and tracked files without modifying repository",
            "confidence": 0.90,
            "cost": 0.05,
            "latency": 0.10,
            "success_rate": 0.80,
        },
    ]

    def __init__(self, memory):
        self.memory = memory

    def bootstrap(self):
        for tool in self.DEFAULT_TOOLS:
            self.memory.upsert_tool(
                tool["id"],
                tool["capability"],
                confidence=tool["confidence"],
                cost=tool["cost"],
                latency=tool["latency"],
                success_rate=tool["success_rate"],
                enabled=True,
            )

    def list_available(self):
        tools = []
        for row in self.memory.list_tools(enabled_only=True):
            tool_id, capability, confidence, cost, latency, last_used, success_rate, enabled, created_at, updated_at = row
            tools.append({
                "id": tool_id,
                "capability": capability,
                "confidence": confidence,
                "cost": cost,
                "latency": latency,
                "last_used": last_used,
                "success_rate": success_rate,
                "enabled": bool(enabled),
            })
        return tools
