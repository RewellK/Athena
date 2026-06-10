import ast
from pathlib import Path


class CodeMapEngine:
    """
    Builds a structural map of Python code using AST.
    It does not depend on specific module names or domain keywords.
    """

    def __init__(self, project_root="."):
        self.project_root = Path(project_root).resolve()

    def build_code_map(self):
        modules = []
        for path in self.project_root.rglob("*.py"):
            if self._ignored(path):
                continue
            modules.append(self._analyze_python_file(path))
        return {
            "project_root": str(self.project_root),
            "modules": sorted(modules, key=lambda item: item["path"]),
            "module_count": len(modules),
        }

    def _ignored(self, path):
        ignored_parts = {".git", "__pycache__", ".venv", "venv", "env"}
        return bool(set(path.relative_to(self.project_root).parts).intersection(ignored_parts))

    def _analyze_python_file(self, path):
        relative = path.relative_to(self.project_root)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception as error:
            return {
                "path": str(relative),
                "classes": [],
                "functions": [],
                "imports": [],
                "docstring": "",
                "parse_error": str(error),
            }

        classes = []
        functions = []
        imports = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "methods": [child.name for child in node.body if isinstance(child, ast.FunctionDef)],
                    "docstring": ast.get_docstring(node) or "",
                })
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)

        return {
            "path": str(relative),
            "classes": classes,
            "functions": functions,
            "imports": sorted(set(imports)),
            "docstring": ast.get_docstring(tree) or "",
            "parse_error": "",
        }
