class ForgettingEngine:

    def __init__(self, memory):
        self.memory = memory

    def forget_expired(self):
        return {
            "short_term_deleted": self.memory.expire_short_term_memory(),
            "mid_term_deleted": self.memory.expire_mid_term_memory(),
        }

    def what_to_forget(self):
        rows = self.memory.list_short_term_memory(include_expired=True)
        if not rows:
            return "Não há memórias curtas candidatas a esquecimento."
        weak = [row for row in rows if row[5] < 10]
        if not weak:
            return "No momento, não vejo nada fraco o bastante para esquecer imediatamente."
        return "Pretendo esquecer memórias curtas fracas ou expiradas:\n" + "\n".join(f"- {row[1]}" for row in weak[:10])
