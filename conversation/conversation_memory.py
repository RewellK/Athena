from collections import deque
from datetime import datetime


class ConversationMemory:
    """Tiny session-only memory for natural variation and recent context."""

    def __init__(self, max_items=30):
        self.items = deque(maxlen=max_items)

    def add(self, speaker, text, route=None, metadata=None):
        self.items.append({
            "speaker": speaker,
            "text": text,
            "route": route,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    def recent(self, limit=8):
        return list(self.items)[-limit:]

    def summary(self, limit=8):
        return "\n".join(
            f"{item.get('speaker')}: {item.get('text')}"
            for item in self.recent(limit)
        )
