from datetime import datetime


class MemoryManager:

    def __init__(self, memory, interpreter=None, creator_name="Rewell"):
        self.memory = memory
        self.interpreter = interpreter
        self.creator_name = creator_name

    def observe(self, content):
        interpretation = self.interpreter.interpret(content) if self.interpreter else self._basic_interpret(content)
        score = interpretation.get("importance_score", 0)
        self.memory.save_short_term_memory(content, score)
        return interpretation

    def maintenance(self):
        expired_short = self.memory.expire_short_term_memory()
        expired_mid = self.memory.expire_mid_term_memory()
        promoted = self.promote_short_to_mid()
        suggestions = self.long_term_candidates()
        return {
            "expired_short": expired_short,
            "expired_mid": expired_mid,
            "promoted_short_to_mid": promoted,
            "long_term_candidates": suggestions,
        }

    def promote_short_to_mid(self):
        rows = self.memory.list_short_term_memory(processed=False)
        terms = self.memory.frequent_terms(rows, min_count=2)
        promoted_count = 0

        for term, count in terms:
            related = [row for row in rows if term in row[1].lower()]
            if not related:
                continue

            avg_score = sum(row[5] for row in related) // len(related)
            importance = avg_score + (count * 10)

            if count >= 2 or importance >= 50:
                summary = f"'{term}' apareceu {count} vezes em memórias recentes."
                self.memory.save_mid_term_memory(
                    summary=summary,
                    topics=[term],
                    source_count=count,
                    importance_score=importance
                )
                self.memory.save_memory_promotion(
                    "short_term",
                    "mid_term",
                    summary,
                    "recorrência detectada em memória curta"
                )
                promoted_count += 1

                for row in related:
                    self.memory.mark_short_term_processed(row[0])

        return promoted_count

    def long_term_candidates(self):
        candidates = []
        mid_rows = self.memory.list_mid_term_memory(promoted=False)

        for row in mid_rows:
            memory_id, summary, topics, source_count, _created_at, _expires_at, importance_score, _promoted = row
            if source_count >= 3 or importance_score >= 70:
                candidates.append({
                    "id": memory_id,
                    "summary": summary,
                    "topics": topics,
                    "reason": "alta recorrência ou importância na memória intermediária"
                })

        return candidates

    def promote_mid_to_long(self, memory_id, content, reason="confirmação do criador"):
        self.memory.save_long_term_memory(content, source="mid_term_promotion", importance_score=90)
        self.memory.save_memory("long_term_consolidation", content)
        self.memory.mark_mid_term_promoted(memory_id)
        self.memory.save_memory_promotion("mid_term", "long_term", content, reason)

    def what_appeared_today(self):
        today = datetime.now().date().isoformat()
        rows = self.memory.list_short_term_memory(created_at_prefix=today)
        terms = self.memory.frequent_terms(rows, min_count=2)

        if not terms:
            return "Hoje ainda não identifiquei temas recorrentes fortes na memória curta."

        lines = ["Hoje estes temas apareceram com mais frequência:"]
        lines.extend(f"- {term}: {count} vezes" for term, count in terms[:10])
        return "\n".join(lines)

    def what_appeared_this_week(self):
        rows = self.memory.list_mid_term_memory()
        if not rows:
            self.promote_short_to_mid()
            rows = self.memory.list_mid_term_memory()

        if not rows:
            return "Nesta semana ainda não identifiquei padrões suficientes na memória intermediária."

        lines = ["Nesta semana, estes padrões estão na memória intermediária:"]
        for _id, summary, topics, source_count, _created_at, _expires_at, importance_score, promoted in rows[:10]:
            status = "promovido" if promoted else "em observação"
            lines.append(f"- {summary} | fontes: {source_count} | score: {importance_score} | {status}")
        return "\n".join(lines)

    def what_to_forget(self):
        rows = self.memory.list_short_term_memory(include_expired=True)
        now = datetime.now().isoformat(timespec="seconds")
        expired = [row for row in rows if row[4] <= now]
        low_value = [row for row in rows if row[5] < 10 and row[4] > now]

        lines = []
        if expired:
            lines.append("Pretendo esquecer memórias curtas expiradas, como:")
            lines.extend(f"- {row[1]}" for row in expired[:5])
        if low_value:
            lines.append("Também posso descartar observações temporárias de baixa importância, como:")
            lines.extend(f"- {row[1]}" for row in low_value[:5])

        if not lines:
            return "No momento, não encontrei nada claramente pronto para ser esquecido."

        return "\n".join(lines)

    def permanent_candidates_answer(self):
        candidates = self.long_term_candidates()
        if not candidates:
            return "Ainda não encontrei padrões fortes o bastante para sugerir memória permanente."

        lines = ["Acho que estes itens podem virar memória permanente, mas preciso de confirmação:"]
        for candidate in candidates[:5]:
            lines.append(f"- {candidate['summary']} | motivo: {candidate['reason']}")
        return "\n".join(lines)

    def _basic_interpret(self, content):
        return {"importance_score": 0, "reason": "interpretação básica", "important": False, "temporary": True}
