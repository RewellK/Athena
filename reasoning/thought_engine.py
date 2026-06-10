from collections import Counter


class ThoughtEngine:
    def __init__(self, memory):
        self.memory = memory

    def generate(self):
        thoughts = []
        for term, count in self._frequent_terms()[:5]:
            thoughts.append({
                "type": "frequency_observation",
                "content": f"{term} aparece com frequência nas memórias.",
                "evidence": [f"{count} ocorrência(s) encontradas em memórias e estruturas."],
                "confidence": min(0.95, 0.45 + (count / 20))
            })
        for entity, degree in self._dense_entities()[:5]:
            thoughts.append({
                "type": "relational_density_observation",
                "content": f"{entity} possui alta densidade relacional no World Model.",
                "evidence": [f"{degree} relação(ões) envolvendo {entity}."],
                "confidence": min(0.95, 0.50 + (degree / 10))
            })
        return thoughts

    def _frequent_terms(self):
        counter = Counter()
        entities = self.memory.list_entities()
        for _id, content, _created_at in self.memory.list_memories():
            lower = content.lower()
            for _eid, name, _etype, _created in entities:
                if name and name.lower() in lower:
                    counter[name] += 1
        for row in self.memory.list_long_term_memory():
            lower = row[1].lower()
            for _eid, name, _etype, _created in entities:
                if name and name.lower() in lower:
                    counter[name] += 1
        try:
            source_items = self.memory.list_knowledge_source_items(limit=200)
        except Exception:
            source_items = []
        for _id, _source_id, _source_name, _category, statement, _confidence, _origin, _evidence, _created_at in source_items:
            lower = statement.lower()
            for _eid, name, _etype, _created in entities:
                if name and name.lower() in lower:
                    counter[name] += 1
        return counter.most_common()

    def _dense_entities(self):
        counter = Counter()
        for _id, source, _relation, target, _confidence, _created_at in self.memory.list_world_relationships():
            counter[source] += 1
            counter[target] += 1
        return counter.most_common()
