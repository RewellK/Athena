class GitStatusReader:
    """Read-only wrapper for git status information."""

    def __init__(self, repository_reader):
        self.repository_reader = repository_reader

    def status(self):
        if not self.repository_reader.git_available():
            return "Não consegui acessar Git nesta máquina."
        if not self.repository_reader.is_repository():
            return "Esta pasta local não parece estar dentro de um repositório Git."
        result = self.repository_reader._run(["status", "--short"])
        if not result["ok"]:
            return "Não consegui ler o status Git: " + result.get("stderr", "erro desconhecido")
        output = result["stdout"].strip()
        return output if output else "A árvore de trabalho não possui alterações aparentes."
