from collections import deque
from datetime import datetime


class ConversationContext:
    """Ephemeral session context.

    This is not persistent memory. It preserves the current desktop/terminal
    conversation flow so Athena can answer naturally without converting every
    phrase into long-term knowledge.
    """

    def __init__(self, max_items=40):
        self.max_items = max_items
        self.messages = deque(maxlen=max_items)
        self.last_route = None

    def add_user_message(self, content, route=None):
        self._add("user", content, route)

    def add_athena_message(self, content, route=None):
        self._add("athena", content, route)
        if route:
            self.last_route = route

    def _add(self, speaker, content, route=None):
        self.messages.append({
            "speaker": speaker,
            "content": str(content or ""),
            "route": route or "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    def recent(self, limit=8):
        return list(self.messages)[-limit:]

    def summary(self, limit=8):
        lines = []
        for item in self.recent(limit):
            speaker = item.get("speaker", "?")
            content = item.get("content", "")
            route = item.get("route")
            suffix = f" [{route}]" if route else ""
            lines.append(f"{speaker}{suffix}: {content}")
        return "\n".join(lines)
