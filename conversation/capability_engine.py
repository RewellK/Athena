class CapabilityEngine:
    """Capability answers are concise by default and technical on request."""

    def __init__(self, self_code_awareness_engine=None, git_awareness_engine=None, voice_engine=None, settings=None):
        self.self_code_awareness_engine = self_code_awareness_engine
        self.git_awareness_engine = git_awareness_engine
        self.voice_engine = voice_engine
        self.settings = settings

    def respond(self, technical=False):
        if technical:
            return self._technical_response()
        return self._summary_response()

    def _summary_response(self):
        voice = "voz" if self._voice_enabled() else "voz opcional"
        git = "leitura Git" if self._git_available() else "leitura Git quando houver repositório local"
        return (
            "Eu posso conversar com você, lembrar informações importantes, consultar meu World Model, "
            "explicar o que sei, mostrar meu status, raciocinar com hipóteses, lidar com ferramentas configuradas "
            "e ajudar você a evoluir meu próprio projeto. "
            f"Também consigo usar {voice} e fazer {git} em modo somente leitura.\n\n"
            "Algumas capacidades ainda dependem de configuração, como clima/notícias em tempo real.\n\n"
            "Se quiser, posso te mostrar isso de forma técnica também."
        )

    def _technical_response(self):
        parts = []
        if self.self_code_awareness_engine:
            try:
                parts.append(self.self_code_awareness_engine.respond({"operation": "capabilities"}))
            except Exception:
                parts.append("Não consegui montar o mapa técnico completo agora.")
        else:
            parts.append("Self Code Awareness indisponível agora.")

        if self.git_awareness_engine:
            try:
                summary = self.git_awareness_engine.summary()
                if summary.get("git_available") and summary.get("is_git_repository"):
                    parts.append(f"Git Awareness: leitura somente, branch atual {summary.get('current_branch')}.")
                elif summary.get("git_available"):
                    parts.append("Git Awareness: Git disponível, mas esta pasta não parece ser um repositório.")
                else:
                    parts.append("Git Awareness: Git indisponível nesta máquina.")
            except Exception:
                parts.append("Git Awareness indisponível no momento.")

        if self.voice_engine:
            try:
                status = self.voice_engine.status()
                parts.append(f"Voice Engine: {status.get('status')} via {status.get('provider')}.")
            except Exception:
                parts.append("Voice Engine: indisponível sem bloquear o núcleo.")

        limitations = []
        if self.self_code_awareness_engine:
            try:
                limitations.append(self.self_code_awareness_engine.respond({"operation": "limitations"}))
            except Exception:
                pass
        if limitations:
            parts.append("Limitações observadas:\n" + "\n".join(limitations))
        return "\n\n".join(parts)

    def _voice_enabled(self):
        try:
            return bool(self.voice_engine and self.voice_engine.status().get("enabled"))
        except Exception:
            return False

    def _git_available(self):
        try:
            summary = self.git_awareness_engine.summary() if self.git_awareness_engine else {}
            return bool(summary.get("git_available") and summary.get("is_git_repository"))
        except Exception:
            return False
