from datetime import datetime


class MemoryManager:

    def __init__(self, memory, interpreter=None, creator_name="Rewell"):
        self.memory = memory
        self.interpreter = interpreter
        self.creator_name = creator_name

    def observe(self, content, relevance=None, consolidation_plan=None, follow_up_question=None):
        if relevance:
            return self._observe_with_relevance(content, relevance, consolidation_plan, follow_up_question)

        interpretation = self.interpreter.interpret(content) if self.interpreter else self._basic_interpret(content)
        score = interpretation.get("importance_score", 0)
        memory_id = self.memory.save_short_term_memory(content, score)
        if hasattr(self.memory, "save_memory_relevance"):
            self.memory.save_memory_relevance(
                "short_term",
                memory_id,
                content,
                self._interpretation_to_relevance(interpretation),
                source_message=content,
            )
        return interpretation

    def _observe_with_relevance(self, content, relevance, consolidation_plan=None, follow_up_question=None):
        relevance = relevance if isinstance(relevance, dict) else {}
        plan = consolidation_plan if isinstance(consolidation_plan, dict) else {}
        score = relevance.get("importance_score", relevance.get("relevance_score", 0))
        priority = str(relevance.get("memory_priority") or "short")
        saved_layers = []
        related_entities = relevance.get("related_entities") if isinstance(relevance.get("related_entities"), list) else []

        if plan.get("store_short_term", priority in {"short", "mid", "long_candidate", "long_confirm"}):
            memory_id = self.memory.save_short_term_memory(content, score)
            saved_layers.append("short_term")
            self.memory.save_memory_relevance(
                "short_term",
                memory_id,
                content,
                relevance,
                source_message=content,
                follow_up_question=follow_up_question,
            )

        if plan.get("store_mid_term", priority in {"mid", "long_candidate", "long_confirm"}):
            memory_id = self.memory.save_mid_term_memory(
                summary=content,
                topics=related_entities,
                source_count=1,
                importance_score=score,
            )
            saved_layers.append("mid_term")
            self.memory.save_memory_relevance(
                "mid_term",
                memory_id,
                content,
                relevance,
                source_message=content,
                follow_up_question=follow_up_question,
            )

        if plan.get("store_long_term_candidate", priority in {"long_candidate", "long_confirm"}):
            saved_layers.append(priority)
            self.memory.save_memory_relevance(
                priority,
                None,
                content,
                relevance,
                source_message=content,
                follow_up_question=follow_up_question,
                confirmed=False,
            )

        result = dict(relevance)
        result["saved_layers"] = saved_layers
        return result

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

        if hasattr(self.memory, "list_long_term_memory_candidates"):
            for row in self.memory.list_long_term_memory_candidates(limit=20):
                (
                    memory_id,
                    layer,
                    _layer_id,
                    content,
                    _source_message,
                    relevance_score,
                    _importance_score,
                    emotional_score,
                    relationship_score,
                    identity_score,
                    future_score,
                    memory_priority,
                    related_entities_json,
                    confirmation_required,
                    _confirmed,
                    _follow_up_question,
                    reason,
                    _created_at,
                ) = row
                candidates.append({
                    "id": memory_id,
                    "summary": content,
                    "topics": related_entities_json,
                    "reason": (
                        reason
                        or f"prioridade={memory_priority}, relevância={relevance_score}, emoção={emotional_score}, relação={relationship_score}, identidade={identity_score}, futuro={future_score}"
                    ),
                    "layer": layer,
                    "confirmation_required": bool(confirmation_required),
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

    def _interpretation_to_relevance(self, interpretation):
        score = interpretation.get("importance_score", 0)
        suggested_layer = interpretation.get("suggested_layer")
        priority = suggested_layer if suggested_layer in {"ignore", "short", "mid", "long_candidate", "long_confirm"} else self._priority_from_score(score)
        return {
            "relevance_score": score,
            "importance_score": score,
            "emotional_score": interpretation.get("emotional_score", 0),
            "relationship_score": interpretation.get("relationship_score", 0),
            "identity_score": interpretation.get("identity_score", 0),
            "future_score": interpretation.get("future_score", 0),
            "memory_priority": priority,
            "related_entities": interpretation.get("related_entities", []),
            "confirmation_required": bool(interpretation.get("needs_confirmation", priority == "long_confirm")),
            "reason": interpretation.get("reason", ""),
        }

    def _priority_from_score(self, score):
        try:
            value = int(score)
        except (TypeError, ValueError):
            value = 0
        if value >= 90:
            return "long_candidate"
        if value >= 75:
            return "long_candidate"
        if value >= 50:
            return "mid"
        if value >= 20:
            return "short"
        return "ignore"
