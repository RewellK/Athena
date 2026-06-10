class LimitationDetector:
    """
    Detects limitations from structural evidence and explicit settings.
    This is not a cognitive parser; it reports operational constraints.
    """

    def detect(self, settings, git_summary=None, gui_available=None):
        limitations = []

        if not settings.get("autoExecuteActions", False):
            limitations.append("Não executo ações irrestritas sem aprovação humana.")
        if not settings.get("autoLearnPermanentKnowledge", False):
            limitations.append("Não transformo conhecimento externo em memória permanente automaticamente.")
        if not settings.get("useLLM", True):
            limitations.append("Minha LLM está desativada nas configurações.")
        if git_summary and not git_summary.get("is_git_repository"):
            limitations.append("Não detectei um repositório Git local nesta pasta.")
        if gui_available is False:
            limitations.append("A interface desktop depende de customtkinter instalado no ambiente.")

        limitations.append("Na V12, Git Awareness é somente leitura: não crio branch, commit, push, pull ou checkout.")
        limitations.append("Ainda não rodo como serviço permanente em segundo plano.")
        return limitations
