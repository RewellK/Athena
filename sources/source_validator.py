from datetime import datetime


class SourceValidator:
    """Safe validator stub. It never scrapes or calls the network in V12.8."""

    def validate(self, source):
        source = dict(source or {})
        if not source:
            return self._result("failed_validation", "failed", "Fonte vazia.")
        if source.get("status") == "rejected":
            return self._result("rejected", "failed", "Fonte rejeitada pelo usuário.")
        if not source.get("url") and source.get("source_type") != "custom_user_source":
            return self._result("pending_validation", "needs_manual_validation", "Fonte sem URL pública para validação.")
        if source.get("requires_api_key") == "yes" and not source.get("credential_key"):
            return self._result("pending_validation", "needs_credentials", "Fonte exige API key, mas nenhuma credencial foi configurada.")
        return self._result(
            "pending_validation",
            "needs_manual_validation",
            "Fonte registrada, mas ainda precisa validação humana/contratual antes de ser habilitada.",
        )

    def _result(self, status, validation_status, reason):
        return {
            "status": status,
            "validation_status": validation_status,
            "validated_at": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "safe_to_enable": validation_status == "passed",
        }
