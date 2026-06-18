class NotificationPolicy:
    def classify(self, source, reason="", importance="normal", urgency="normal", requires_user_approval=False):
        source = str(source or "runtime")
        importance = str(importance or "normal")
        urgency = str(urgency or "normal")
        interrupt = bool(
            requires_user_approval
            or urgency in {"high", "critical"}
            or importance in {"high", "critical"}
            or source in {"safe_mode", "worker_failure"}
        )
        return {
            "source": source,
            "reason": str(reason or ""),
            "importance": importance,
            "urgency": urgency,
            "requires_interruption": interrupt,
            "can_wait_for_briefing": not interrupt,
        }
