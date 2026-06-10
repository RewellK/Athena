class GitHistoryReader:
    """Read-only wrapper for commit history."""

    def __init__(self, repository_reader):
        self.repository_reader = repository_reader

    def recent_commits(self, limit=8):
        if not self.repository_reader.git_available():
            return []
        if not self.repository_reader.is_repository():
            return []
        result = self.repository_reader._run(["log", "--oneline", "--decorate", "-n", str(limit)])
        if not result["ok"] or not result["stdout"].strip():
            return []
        return result["stdout"].strip().splitlines()

    def history_summary(self, limit=8):
        commits = self.recent_commits(limit=limit)
        if not commits:
            return "Não encontrei histórico Git local para resumir."
        lines = ["Minha evolução recente observada no Git local:"]
        for commit in commits:
            lines.append(f"- {commit}")
        return "\n".join(lines)
