from self_code_awareness.capability_mapper import CapabilityMapper
from self_code_awareness.code_map_engine import CodeMapEngine
from self_code_awareness.limitation_detector import LimitationDetector
from self_code_awareness.module_analyzer import ModuleAnalyzer
from self_code_awareness.project_scanner import ProjectScanner


class ArchitectureMemory:
    """
    Gives Athena read-only awareness of her local operational body.
    """

    def __init__(self, project_root=".", settings=None, git_reader=None):
        self.project_root = project_root
        self.settings = settings
        self.git_reader = git_reader
        self.project_scanner = ProjectScanner(project_root)
        self.code_map_engine = CodeMapEngine(project_root)
        self.module_analyzer = ModuleAnalyzer()
        self.capability_mapper = CapabilityMapper()
        self.limitation_detector = LimitationDetector()

    def snapshot(self):
        scan = self.project_scanner.scan()
        code_map = self.code_map_engine.build_code_map()
        modules = self.module_analyzer.analyze(code_map)
        capabilities = self.capability_mapper.map_capabilities(modules)
        git_summary = self.git_reader.summary() if self.git_reader else None
        settings_values = self.settings.values if self.settings else {}
        limitations = self.limitation_detector.detect(settings_values, git_summary=git_summary)
        return {
            "scan": scan,
            "code_map": code_map,
            "modules": modules,
            "capabilities": capabilities,
            "limitations": limitations,
            "git": git_summary,
        }

    def describe_body(self):
        snapshot = self.snapshot()
        modules = snapshot["modules"]
        lines = ["Sou formada por módulos Python organizados na minha pasta local."]
        lines.append(f"Analisei {snapshot['scan']['file_count']} arquivos e {len(modules)} áreas de código.")
        lines.append("Principais áreas observadas:")
        for item in modules[:12]:
            lines.append(
                f"- {item['package']}: {item['files']} arquivo(s), "
                f"{item['classes']} classe(s), {item['functions']} função(ões)."
            )
        return "\n".join(lines)

    def describe_capabilities(self):
        snapshot = self.snapshot()
        lines = ["Minhas capacidades observadas a partir da estrutura real do código são:"]
        for item in snapshot["capabilities"][:16]:
            evidence = ", ".join(item.get("classes", [])[:3]) or "estrutura de arquivos"
            lines.append(f"- {item['area']} ({item['package']}): evidência: {evidence}.")
        lines.append("\nLimitações atuais:")
        for limitation in snapshot["limitations"]:
            lines.append(f"- {limitation}")
        return "\n".join(lines)

    def describe_limitations(self):
        snapshot = self.snapshot()
        lines = ["Minhas limitações atuais, baseadas em configuração e estrutura local:"]
        for limitation in snapshot["limitations"]:
            lines.append(f"- {limitation}")
        return "\n".join(lines)

    def weakest_area(self):
        snapshot = self.snapshot()
        modules = snapshot["modules"]
        if not modules:
            return "Ainda não encontrei módulos suficientes para avaliar fragilidade estrutural."
        ordered = sorted(modules, key=lambda item: (item["classes"] + item["functions"], item["files"]))
        weakest = ordered[0]
        return (
            "A área estruturalmente mais fraca parece ser "
            f"'{weakest['package']}', porque possui pouca superfície de código observável: "
            f"{weakest['files']} arquivo(s), {weakest['classes']} classe(s), "
            f"{weakest['functions']} função(ões). Isso não prova baixa qualidade; apenas indica menor evidência estrutural."
        )

    def version_changes(self):
        if self.git_reader:
            return self.git_reader.history_summary()
        return "Não há leitor Git configurado para analisar evolução entre versões."
