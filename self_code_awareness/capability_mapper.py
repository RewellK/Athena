class CapabilityMapper:
    """
    Produces capability descriptions from observed modules/classes/docstrings.
    No fixed module catalogue is used; the codebase itself is the source.
    """

    def map_capabilities(self, module_analysis):
        capabilities = []
        for package in module_analysis:
            name = package.get("package", ".")
            classes = package.get("public_classes", [])
            functions = package.get("public_functions", [])
            evidence = package.get("evidence", [])
            capability_name = self._humanize(name)
            capabilities.append({
                "area": capability_name,
                "package": name,
                "classes": classes,
                "functions": functions,
                "evidence": evidence,
                "confidence": self._confidence(package),
            })
        return capabilities

    def _humanize(self, text):
        normalized = text.replace("_", " ").replace("-", " ").strip()
        return normalized.title() if normalized else "Root"

    def _confidence(self, package):
        score = 0.35
        score += min(package.get("files", 0) * 0.05, 0.25)
        score += min(package.get("classes", 0) * 0.05, 0.25)
        score += min(len(package.get("evidence", [])) * 0.05, 0.15)
        return round(min(score, 1.0), 2)
