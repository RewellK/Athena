class SelfStatusEngine:
    """Formats health snapshots for conversational status questions."""

    def __init__(self, health_engine=None, error_capture=None):
        self.health_engine = health_engine
        self.error_capture = error_capture

    def respond(self):
        if not self.health_engine:
            return "Estou funcional, mas o Health Engine não está disponível para detalhar meu estado agora."
        snapshot = self.health_engine.snapshot()
        lines = [
            "Estou operacional." if snapshot.get("overall") == "operational" else "Estou parcialmente operacional.",
            f"LLM: {snapshot.get('llm', {}).get('status', 'desconhecida')}",
            f"Banco: {snapshot.get('sqlite', {}).get('status', 'desconhecido')}",
            f"Git: {snapshot.get('git', {}).get('status', 'desconhecido')}",
            f"Voz: {snapshot.get('voice', {}).get('status', 'desconhecida')}",
            f"Memórias: {snapshot.get('memory', {}).get('memories', 0)} registros",
            f"Entidades: {snapshot.get('world', {}).get('entities', 0)}",
            f"Intenções: {snapshot.get('agency', {}).get('intentions', 0)}",
            f"Planos: {snapshot.get('agency', {}).get('plans', 0)}",
        ]
        last_error = snapshot.get("last_error")
        if last_error:
            analysis = last_error.get("analysis", {})
            lines.append(f"Último erro: {analysis.get('title', last_error.get('error_type', 'erro registrado'))} — gravidade {analysis.get('severity', 'médio')}.")
        else:
            lines.append("Último erro: nenhum registrado.")
        return "\n".join(lines)
