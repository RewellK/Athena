class CapabilityEngine:
    """Capability answers are generated from observed modules when possible."""

    def __init__(self, self_code_awareness_engine=None, git_awareness_engine=None, voice_engine=None, settings=None):
        self.self_code_awareness_engine = self_code_awareness_engine
        self.git_awareness_engine = git_awareness_engine
        self.voice_engine = voice_engine
        self.settings = settings

    def respond(self):
        parts = []
        if self.self_code_awareness_engine:
            try:
                parts.append(self.self_code_awareness_engine.respond({"operation": "capabilities"}))
            except Exception:
                parts.append("Consigo analisar minha estrutura local, mas houve falha ao montar o mapa completo de capacidades agora.")
        else:
            parts.append("Consigo conversar, usar memória interna e consultar meu estado, mas o mapeamento de código não está disponível agora.")

        limitations = []
        if self.self_code_awareness_engine:
            try:
                limitations.append(self.self_code_awareness_engine.respond({"operation": "limitations"}))
            except Exception:
                pass

        git_text = ""
        if self.git_awareness_engine:
            try:
                summary = self.git_awareness_engine.summary()
                if summary.get("git_available") and summary.get("is_git_repository"):
                    git_text = f"\nTambém consigo ler meu repositório Git em modo somente leitura. Branch atual: {summary.get('current_branch')}"
                elif summary.get("git_available"):
                    git_text = "\nGit está disponível, mas não detectei repositório local nesta pasta."
                else:
                    git_text = "\nNão consegui acessar Git nesta máquina agora."
            except Exception:
                git_text = "\nGit Awareness está indisponível no momento."

        voice_text = ""
        if self.voice_engine:
            try:
                status = self.voice_engine.status()
                voice_text = f"\nVoz: {status.get('status')} via {status.get('provider')}."
            except Exception:
                voice_text = "\nVoz: indisponível no momento, sem bloquear o núcleo."

        final = "\n\n".join(parts)
        if limitations:
            final += "\n\nLimitações observadas:\n" + "\n".join(limitations)
        return final + git_text + voice_text
