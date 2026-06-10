class ErrorAnalyzer:
    """Operational error analyzer.

    This module does not interpret user meaning. It classifies technical failures
    so Athena can explain them without exposing raw stacktraces.
    """

    def analyze(self, error, stacktrace="", context=None):
        context = context or {}
        error_text = f"{type(error).__name__}: {error}\n{stacktrace}"
        lowered = error_text.lower()

        analysis = {
            "title": "Falha interna inesperada",
            "severity": "médio",
            "probable_module": context.get("module", "módulo não identificado"),
            "impact": "A operação atual pode não ter sido concluída, mas a Athena deve continuar funcionando.",
            "friendly_explanation": "Encontrei uma falha interna durante o processamento.",
            "suggestions": [
                "Verificar logs/errors.log para o stacktrace técnico.",
                "Repetir a operação após atualizar o estado da GUI."
            ],
        }

        if "sqlite objects created in a thread" in lowered or "check_same_thread" in lowered:
            analysis.update({
                "title": "Conflito de thread no SQLite",
                "severity": "alto",
                "probable_module": "memory/database.py e camada GUI/background_tasks",
                "friendly_explanation": (
                    "A GUI executou uma operação em uma thread diferente daquela associada ao banco SQLite. "
                    "Isso pode acontecer quando a conversa roda em background para manter a janela responsiva."
                ),
                "suggestions": [
                    "Usar conexão SQLite com check_same_thread=False.",
                    "Proteger execute/commit/fetch com threading.RLock.",
                    "Executar tarefas longas por uma fila de background controlada."
                ],
            })
        elif "database is locked" in lowered:
            analysis.update({
                "title": "Banco SQLite ocupado",
                "severity": "alto",
                "probable_module": "memory/database.py",
                "friendly_explanation": "O SQLite recusou uma operação porque outra operação ainda segurava o banco.",
                "suggestions": [
                    "Manter WAL habilitado.",
                    "Aumentar busy_timeout.",
                    "Garantir lock compartilhado entre operações críticas."
                ],
            })
        elif "no such table" in lowered:
            analysis.update({
                "title": "Tabela ausente no SQLite",
                "severity": "alto",
                "probable_module": "bootstrap.py ou memory/database.py",
                "friendly_explanation": "Uma tabela esperada não existe no banco local.",
                "suggestions": [
                    "Executar bootstrap automático na inicialização.",
                    "Garantir que create_tables cubra todas as tabelas atuais."
                ],
            })
        elif "customtkinter" in lowered:
            analysis.update({
                "title": "Dependência de GUI ausente",
                "severity": "baixo",
                "probable_module": "app.py/gui",
                "friendly_explanation": "A interface desktop depende do CustomTkinter, que não está disponível neste ambiente.",
                "suggestions": ["Instalar com: pip install customtkinter", "Usar python main.py enquanto a dependência não estiver instalada."],
            })
        elif "urlopen" in lowered or "connection refused" in lowered or "timed out" in lowered:
            analysis.update({
                "title": "Serviço externo indisponível",
                "severity": "médio",
                "probable_module": context.get("module", "llm/provider.py ou git_awareness"),
                "friendly_explanation": "Uma chamada externa demorou ou falhou.",
                "suggestions": ["Verificar se Ollama está ativo.", "Atualizar status pela GUI.", "Continuar usando memória interna se a LLM estiver indisponível."],
            })

        return analysis
