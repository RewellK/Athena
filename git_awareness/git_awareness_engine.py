from git_awareness.git_diff_reader import GitDiffReader
from git_awareness.git_history_reader import GitHistoryReader
from git_awareness.git_repository_reader import GitRepositoryReader
from git_awareness.git_status_reader import GitStatusReader


class GitAwarenessEngine:
    """
    Coordinates read-only Git awareness.
    The requested operation must come from structured intention, not keywords.
    """

    READ_OPERATIONS = {
        "summary",
        "status",
        "branch",
        "history",
        "diff",
        "tracked_files",
        "read_only_policy",
    }

    def __init__(self, repo_path=".", official_repository_url="https://github.com/RewellK/Athena/"):
        self.repository_reader = GitRepositoryReader(repo_path, official_repository_url)
        self.status_reader = GitStatusReader(self.repository_reader)
        self.history_reader = GitHistoryReader(self.repository_reader)
        self.diff_reader = GitDiffReader(self.repository_reader)

    def summary(self):
        return self.repository_reader.summary()

    def respond(self, structured_request=None):
        request = structured_request if isinstance(structured_request, dict) else {}
        operation = str(request.get("operation") or "summary").strip().lower()

        if operation not in self.READ_OPERATIONS:
            return self.repository_reader.explain_read_only_policy(operation)

        if operation == "status":
            return self.status_reader.status()
        if operation == "branch":
            summary = self.repository_reader.summary()
            if not summary.get("git_available"):
                return summary.get("message", "Não consegui acessar Git nesta máquina.")
            if not summary.get("is_git_repository"):
                return "Esta pasta local não parece estar dentro de um repositório Git."
            return f"Branch atual: {summary.get('current_branch')}."
        if operation == "history":
            return self.history_reader.history_summary()
        if operation == "diff":
            return self.diff_reader.diff_summary()
        if operation == "tracked_files":
            files = self.repository_reader.tracked_files(limit=40)
            if not files:
                return "Não encontrei arquivos versionados para listar."
            return "Arquivos versionados observados:\n" + "\n".join(f"- {item}" for item in files)
        if operation == "read_only_policy":
            return self.repository_reader.explain_read_only_policy()
        return self._format_summary(self.repository_reader.summary())

    def history_summary(self):
        return self.history_reader.history_summary()

    def _format_summary(self, summary):
        if not summary.get("git_available"):
            return summary.get("message", "Não consegui acessar Git nesta máquina.")
        if not summary.get("is_git_repository"):
            return (
                "Não detectei um repositório Git local nesta pasta.\n"
                f"Origem pública conhecida: {summary.get('official_repository_url')}"
            )
        lines = [
            "Detectei um repositório Git local em modo somente leitura.",
            f"Raiz: {summary.get('root')}",
            f"Branch atual: {summary.get('current_branch')}",
            f"Origem pública conhecida: {summary.get('official_repository_url')}",
        ]
        remotes = summary.get("remotes", [])
        if remotes:
            lines.append("Remotes:")
            lines.extend(f"- {item}" for item in remotes[:6])
        return "\n".join(lines)
