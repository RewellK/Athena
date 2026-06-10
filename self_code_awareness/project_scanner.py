from pathlib import Path


class ProjectScanner:
    """
    Reads the local project structure without interpreting domain meaning.
    This scanner treats files as evidence about Athena's operational body.
    """

    DEFAULT_IGNORED_DIRECTORIES = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "env",
        "logs",
    }

    DEFAULT_IGNORED_SUFFIXES = {
        ".pyc",
        ".db",
        ".sqlite",
        ".zip",
        ".wav",
        ".mp3",
    }

    def __init__(self, project_root="."):
        self.project_root = Path(project_root).resolve()

    def scan(self):
        files = []
        directories = set()

        for path in self.project_root.rglob("*"):
            relative = path.relative_to(self.project_root)
            parts = set(relative.parts)
            if parts.intersection(self.DEFAULT_IGNORED_DIRECTORIES):
                continue
            if path.is_dir():
                directories.add(str(relative))
                continue
            if path.suffix in self.DEFAULT_IGNORED_SUFFIXES:
                continue
            files.append(self._file_entry(path, relative))

        return {
            "project_root": str(self.project_root),
            "directories": sorted(directories),
            "files": sorted(files, key=lambda item: item["path"]),
            "file_count": len(files),
            "directory_count": len(directories),
        }

    def _file_entry(self, path, relative):
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
            readable = True
        except UnicodeDecodeError:
            lines = []
            readable = False
        return {
            "path": str(relative),
            "name": path.name,
            "suffix": path.suffix,
            "size_bytes": path.stat().st_size,
            "line_count": len(lines),
            "readable_text": readable,
        }
