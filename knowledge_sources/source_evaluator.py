from datetime import datetime


class SourceEvaluator:
    """
    Avalia fontes de forma genérica.

    Este módulo não conhece domínios, sites, APIs ou temas específicos.
    Ele avalia sinais estruturais da fonte: origem declarada, autoria,
    data, rastreabilidade, consistência e confiança informada pelo usuário.
    """

    def evaluate(self, source_name, source_type="unknown", origin="user_supplied", metadata=None, content=""):
        metadata = metadata or {}
        confidence = 0.50
        reasons = []

        if source_name:
            confidence += 0.08
            reasons.append("fonte possui nome declarado")

        if origin:
            confidence += 0.08
            reasons.append("origem declarada")

        if source_type and source_type != "unknown":
            confidence += 0.05
            reasons.append("tipo de fonte declarado")

        if metadata.get("author"):
            confidence += 0.08
            reasons.append("autoria declarada")

        if metadata.get("published_at") or metadata.get("timestamp"):
            confidence += 0.06
            reasons.append("data ou timestamp disponível")

        if metadata.get("traceable") is True:
            confidence += 0.10
            reasons.append("fonte rastreável")

        if metadata.get("user_trust_score") is not None:
            user_score = self._normalize_score(metadata.get("user_trust_score"))
            confidence = (confidence + user_score) / 2
            reasons.append("confiança informada pelo usuário considerada")

        content_length = len((content or "").strip())
        if content_length >= 800:
            confidence += 0.05
            reasons.append("conteúdo possui contexto suficiente")
        elif content_length < 80:
            confidence -= 0.10
            reasons.append("conteúdo curto demais para alta confiança")

        if metadata.get("anonymous") is True:
            confidence -= 0.10
            reasons.append("fonte anônima")

        confidence = max(0.0, min(1.0, confidence))

        return {
            "source_name": source_name or "fonte_sem_nome",
            "source_type": source_type or "unknown",
            "origin": origin or "unknown",
            "confidence": confidence,
            "rationale": "; ".join(reasons) if reasons else "avaliação genérica sem sinais adicionais",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "metadata": metadata,
        }

    def _normalize_score(self, value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.50
        if numeric > 1:
            numeric = numeric / 100
        return max(0.0, min(1.0, numeric))
