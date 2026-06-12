from collections import deque
from datetime import datetime
from difflib import SequenceMatcher
import unicodedata


class ConversationContext:
    """Ephemeral session context.

    This is not persistent memory. It preserves the current desktop/terminal
    conversation flow so Athena can answer naturally without converting every
    phrase into long-term knowledge.
    """

    def __init__(self, max_items=40):
        self.max_items = max_items
        self.messages = deque(maxlen=max_items)
        self.entity_mentions = deque(maxlen=max_items)
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

    def remember_entity(self, name, entity_type="unknown", source="conversation"):
        name = str(name or "").strip()
        if not name:
            return
        normalized = self._normalize(name)
        if not normalized:
            return
        self.entity_mentions.append({
            "name": name,
            "normalized": normalized,
            "entity_type": str(entity_type or "unknown").strip() or "unknown",
            "source": source,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    def recent_entities(self, limit=8):
        return list(self.entity_mentions)[-limit:]

    def resolve_entity_reference(self, reference, threshold=0.84):
        normalized = self._normalize(reference)
        if not normalized:
            return ""
        recent = list(reversed(self.recent_entities(limit=12)))
        if not recent:
            return ""

        if normalized in {"ela", "dela", "nela", "ele", "dele", "nele", "isso", "disso", "nisso"}:
            return recent[0].get("name", "")

        for entity in recent:
            if normalized == entity.get("normalized"):
                return entity.get("name", "")

        best = ("", 0.0)
        for entity in recent:
            candidate = entity.get("normalized", "")
            if not candidate:
                continue
            ratio = SequenceMatcher(None, normalized, candidate).ratio()
            if ratio > best[1]:
                best = (entity.get("name", ""), ratio)
        return best[0] if best[1] >= threshold else ""

    def _normalize(self, text):
        normalized = unicodedata.normalize("NFKD", str(text or "").strip().lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        chars = []
        for char in normalized:
            chars.append(char if char.isalnum() else " ")
        return " ".join("".join(chars).split())
