from collections import defaultdict


class ModuleAnalyzer:
    """
    Aggregates code-map evidence by filesystem package.
    Package names are read from the actual folder structure.
    """

    def analyze(self, code_map):
        packages = defaultdict(lambda: {
            "files": 0,
            "classes": 0,
            "functions": 0,
            "public_classes": [],
            "public_functions": [],
            "docstrings": [],
        })

        for module in code_map.get("modules", []):
            path = module.get("path", "")
            package = path.split("/")[0] if "/" in path else "."
            entry = packages[package]
            entry["files"] += 1
            entry["classes"] += len(module.get("classes", []))
            entry["functions"] += len(module.get("functions", []))
            entry["public_classes"].extend(item.get("name") for item in module.get("classes", []) if item.get("name"))
            entry["public_functions"].extend(item for item in module.get("functions", []) if item and not item.startswith("_"))
            if module.get("docstring"):
                entry["docstrings"].append(module.get("docstring"))
            for class_item in module.get("classes", []):
                if class_item.get("docstring"):
                    entry["docstrings"].append(class_item.get("docstring"))

        result = []
        for name, data in packages.items():
            result.append({
                "package": name,
                "files": data["files"],
                "classes": data["classes"],
                "functions": data["functions"],
                "public_classes": sorted(set(data["public_classes"])),
                "public_functions": sorted(set(data["public_functions"])),
                "evidence": data["docstrings"][:3],
            })
        return sorted(result, key=lambda item: item["package"])
