class ErrorReporter:
    """Formats technical error analysis into user-safe explanations."""

    def friendly_message(self, captured):
        analysis = captured.get("analysis", {}) if captured else {}
        title = analysis.get("title", "Falha interna")
        explanation = analysis.get("friendly_explanation", "Encontrei uma falha interna.")
        module = analysis.get("probable_module", "módulo não identificado")
        severity = analysis.get("severity", "médio")
        return (
            f"Encontrei uma falha interna ao processar sua mensagem.\n\n"
            f"O que aconteceu: {title}. {explanation}\n"
            f"Onde provavelmente corrigir: {module}.\n"
            f"Gravidade: {severity}.\n\n"
            f"Detalhes técnicos foram registrados nos logs. Vou continuar operando normalmente."
        )

    def explain_last_error(self, captured, focus=None):
        if not captured:
            return "Não encontrei erro recente registrado."
        analysis = captured.get("analysis", {})
        if focus == "where":
            return f"O ponto provável de correção é: {analysis.get('probable_module', 'módulo não identificado')}."
        if focus == "severity":
            return f"Classifico esse erro como gravidade {analysis.get('severity', 'médio')}."
        suggestions = analysis.get("suggestions", [])
        suggestion_text = "\n".join(f"- {item}" for item in suggestions) if suggestions else "- Verificar logs/errors.log."
        return (
            f"Último erro registrado: {analysis.get('title', captured.get('error_type'))}.\n"
            f"Explicação: {analysis.get('friendly_explanation', captured.get('error', ''))}\n"
            f"Módulo provável: {analysis.get('probable_module', 'não identificado')}\n"
            f"Gravidade: {analysis.get('severity', 'médio')}\n"
            f"Sugestões:\n{suggestion_text}"
        )
