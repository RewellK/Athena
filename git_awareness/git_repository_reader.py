import shutil
import subprocess
from pathlib import Path


class GitRepositoryReader:
    """
    Read-only Git repository awareness.
    Every command used here is informational. No checkout, commit, push, pull,
    branch creation, reset, merge, or file mutation is implemented.
    """

    READ_ONLY_COMMANDS = {
        "is_repo": ["rev-parse", "--is-inside-work-tree"],
        "root": ["rev-parse", "--show-toplevel"],
        "branch": ["branch", "--show-current"],
        "remote": ["remote", "-v"],
        "status": ["status", "--short"],
        "log": ["log", "--oneline", "--decorate", "-n"],
        "tracked_files": ["ls-files"],
    }

    MUTATING_OPERATIONS = {
        "commit",
        "push",
        "pull",
        "checkout",
        "switch",
        "branch_create",
        "branch_delete",
        "merge",
        "rebase",
        "reset",
        "tag",
        "stash",
        "add",
        "restore",
    }

    def __init__(self, repo_path=".", official_repository_url="https://github.com/RewellK/Athena/"):
        self.repo_path = Path(repo_path).resolve()
        self.official_repository_url = official_repository_url

    def git_available(self):
        return shutil.which("git") is not None

    def is_repository(self):
        result = self._run(self.READ_ONLY_COMMANDS["is_repo"])
        return result["ok"] and result["stdout"].strip().lower() == "true"

    def root(self):
        result = self._run(self.READ_ONLY_COMMANDS["root"])
        return result["stdout"].strip() if result["ok"] else ""

    def current_branch(self):
        result = self._run(self.READ_ONLY_COMMANDS["branch"])
        if result["ok"] and result["stdout"].strip():
            return result["stdout"].strip()
        return "branch indisponível"

    def remotes(self):
        result = self._run(self.READ_ONLY_COMMANDS["remote"])
        return result["stdout"].strip().splitlines() if result["ok"] and result["stdout"].strip() else []

    def tracked_files(self, limit=50):
        result = self._run(self.READ_ONLY_COMMANDS["tracked_files"])
        if not result["ok"] or not result["stdout"].strip():
            return []
        return result["stdout"].strip().splitlines()[:limit]

    def summary(self):
        if not self.git_available():
            return {
                "git_available": False,
                "is_git_repository": False,
                "official_repository_url": self.official_repository_url,
                "message": "Não consegui acessar Git nesta máquina.",
            }
        is_repo = self.is_repository()
        return {
            "git_available": True,
            "is_git_repository": is_repo,
            "root": self.root() if is_repo else "",
            "current_branch": self.current_branch() if is_repo else "",
            "remotes": self.remotes() if is_repo else [],
            "official_repository_url": self.official_repository_url,
            "tracked_files_sample": self.tracked_files() if is_repo else [],
            "mode": "read_only",
        }

    def explain_read_only_policy(self, requested_operation=""):
        operation = str(requested_operation or "").strip().lower()
        if operation in self.MUTATING_OPERATIONS:
            return (
                "Na V12 eu só posso ler o Git. Ainda não posso alterar branches, "
                "criar commits, executar push, pull ou modificar arquivos."
            )
        return (
            "Meu Git Awareness está em modo somente leitura. Posso consultar status, "
            "branch, histórico e arquivos versionados, mas não altero o repositório."
        )

    def _run(self, args):
        if not self.git_available():
            return {"ok": False, "stdout": "", "stderr": "git indisponível"}
        try:
            completed = subprocess.run(
                ["git"] + list(args),
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return {
                "ok": completed.returncode == 0,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "command": "git " + " ".join(args),
            }
        except Exception as error:
            return {"ok": False, "stdout": "", "stderr": str(error)}
