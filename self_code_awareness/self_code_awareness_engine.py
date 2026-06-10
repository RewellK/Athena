from self_code_awareness.architecture_memory import ArchitectureMemory


class SelfCodeAwarenessEngine:
    """
    Coordinates Athena's read-only awareness of her own local code.
    Operations are selected from structured intention, not from user wording.
    """

    OPERATIONS = {
        "body",
        "modules",
        "capabilities",
        "limitations",
        "weakest_area",
        "version_changes",
        "snapshot",
    }

    def __init__(self, project_root=".", settings=None, git_reader=None):
        self.architecture_memory = ArchitectureMemory(project_root, settings=settings, git_reader=git_reader)

    def respond(self, structured_request=None):
        request = structured_request if isinstance(structured_request, dict) else {}
        operation = str(request.get("operation") or "body").strip().lower()
        if operation not in self.OPERATIONS:
            operation = "body"

        if operation == "modules":
            return self._modules()
        if operation == "capabilities":
            return self.architecture_memory.describe_capabilities()
        if operation == "limitations":
            return self.architecture_memory.describe_limitations()
        if operation == "weakest_area":
            return self.architecture_memory.weakest_area()
        if operation == "version_changes":
            return self.architecture_memory.version_changes()
        if operation == "snapshot":
            return self._snapshot_summary()
        return self.architecture_memory.describe_body()

    def _modules(self):
        snapshot = self.architecture_memory.snapshot()
        lines = ["Módulos observados na minha estrutura local:"]
        for item in snapshot.get("modules", []):
            classes = ", ".join(item.get("public_classes", [])[:4]) or "sem classes públicas observadas"
            lines.append(f"- {item['package']}: {item['files']} arquivo(s). Evidência: {classes}.")
        return "\n".join(lines)

    def _snapshot_summary(self):
        snapshot = self.architecture_memory.snapshot()
        return (
            "Snapshot estrutural local:\n"
            f"- Arquivos: {snapshot['scan']['file_count']}\n"
            f"- Diretórios: {snapshot['scan']['directory_count']}\n"
            f"- Módulos Python: {snapshot['code_map']['module_count']}\n"
            f"- Áreas analisadas: {len(snapshot['modules'])}\n"
            f"- Git detectado: {bool(snapshot.get('git', {}).get('is_git_repository'))}"
        )
