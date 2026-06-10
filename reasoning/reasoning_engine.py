import json
from datetime import datetime

from reasoning.thought_engine import ThoughtEngine


class ReasoningEngine:
    """
    V11 structural reasoning.
    The engine receives questions routed by IntentionEngine and reasons from
    evidence. It does not dispatch behaviour through keyword commands.
    """

    def __init__(self, memory, identity, llm_provider=None, context_builder=None, logger=None):
        self.memory = memory
        self.identity = identity
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger
        self.thought_engine = ThoughtEngine(memory)
        self.last_conclusion = None

    def respond(self, user_input, intention=None):
        request = intention.get("structured_request") if isinstance(intention, dict) and isinstance(intention.get("structured_request"), dict) else {}
        if request.get("operation") == "explain_last_conclusion":
            return self.explain_last_conclusion()
        conclusion = self.reason_about_question(user_input)
        if conclusion:
            self.last_conclusion = conclusion
            return self._format_conclusion(conclusion)
        return self._summary_response(user_input)

    def answer(self, user_input):
        return self.respond(user_input)

    def known_facts(self):
        facts = self._evidence_context()
        return "O que eu sei:\n" + "\n".join(facts[:40]) if facts else "Ainda não possuo conhecimentos estruturados suficientes para listar."

    def beliefs_summary(self):
        rows = self.memory.list_reasoning_conclusions("belief")
        return "O que eu acredito:\n" + "\n".join(self._row_to_line(row) for row in rows[:20]) if rows else "Ainda não possuo crenças sustentadas por evidências suficientes."

    def hypotheses_summary(self):
        rows = self.memory.list_reasoning_conclusions("hypothesis")
        return "Hipóteses atuais:\n" + "\n".join(self._row_to_line(row) for row in rows[:20]) if rows else "Ainda não possuo hipóteses relevantes."

    def unknowns_summary(self):
        thoughts = self.thought_engine.generate()
        if not thoughts:
            return "Ainda não tenho dados suficientes para apontar grandes lacunas."
        return "Ainda não entendo completamente algumas conexões recorrentes:\n" + "\n".join(f"- {t['content']}" for t in thoughts[:5])

    def reason_about_question(self, user_input):
        if not self.llm_provider:
            return None
        facts = self._evidence_context()
        if not facts:
            return None
        prompt = self._build_reasoning_prompt(user_input, facts)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            parsed = self._parse_json(result.text)
            conclusion = self._normalize_conclusion(parsed)
            if not conclusion or not conclusion.get("should_reason"):
                return None
            if conclusion["confidence"] >= 0.50:
                self.memory.save_reasoning_conclusion(
                    category=conclusion["category"],
                    statement=conclusion["statement"],
                    confidence=conclusion["confidence"],
                    evidence=conclusion.get("evidence", []),
                    origin=conclusion["origin"],
                    created_at=conclusion["created_at"],
                )
            return conclusion
        except Exception as error:
            if self.logger:
                self.logger.log("REASONING_ERROR", str(error))
            return None

    def generate_beliefs(self):
        return self._generate_from_thoughts("belief", minimum_confidence=0.70)

    def generate_hypotheses(self):
        return self._generate_from_thoughts("hypothesis", minimum_confidence=0.50)

    def explain_last_conclusion(self):
        conclusion = self.last_conclusion
        if not conclusion:
            rows = self.memory.list_reasoning_conclusions()
            if rows:
                conclusion = self._row_to_dict(rows[0])
        if not conclusion:
            return "Ainda não tenho uma conclusão recente para explicar."
        evidence_lines = "\n".join(f"- {item}" for item in conclusion.get("evidence", []))
        return f"Conclusão: {conclusion['statement']}\nCategoria: {conclusion['category']}\nConfiança: {conclusion['confidence']:.2f}\nOrigem: {conclusion['origin']}\nEvidências:\n{evidence_lines}"

    def self_reflection(self):
        return {
            "knowledge_count": len(self.memory.list_world_relationships()) + len(self.memory.list_entity_states()) + self.memory.count_knowledge_source_items("knowledge"),
            "belief_count": self.memory.count_reasoning_conclusions("belief"),
            "hypothesis_count": self.memory.count_reasoning_conclusions("hypothesis"),
            "thoughts": self.thought_engine.generate(),
        }

    def _generate_from_thoughts(self, category, minimum_confidence):
        generated = []
        for thought in self.thought_engine.generate():
            confidence = float(thought.get("confidence", 0.50))
            if confidence < minimum_confidence:
                continue
            statement = thought.get("content", "").strip()
            if not statement:
                continue
            conclusion = {
                "category": category,
                "statement": statement,
                "confidence": confidence,
                "evidence": thought.get("evidence", []),
                "origin": f"thought_engine:{thought.get('type', 'observation')}",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            self.memory.save_reasoning_conclusion(**conclusion)
            generated.append(conclusion)
        return generated

    def _summary_response(self, user_input):
        if self.llm_provider:
            evidence = {
                "facts": self._evidence_context()[:40],
                "beliefs": self.memory.list_reasoning_conclusions("belief")[:10],
                "hypotheses": self.memory.list_reasoning_conclusions("hypothesis")[:10],
                "thoughts": self.thought_engine.generate()[:10],
            }
            prompt = f"""
Você é o Reasoning Engine da Athena.
Responda usando apenas evidências estruturadas.
Diferencie conhecimento, crença e hipótese.
Se não houver evidência suficiente, diga isso.

Pedido:
{user_input}

Evidências:
{json.dumps(evidence, ensure_ascii=False, indent=2)}
""".strip()
            result = self.llm_provider.generate(prompt)
            if result.available and result.text:
                return result.text.strip()
        return "Ainda não tenho evidências suficientes para raciocinar sobre isso com segurança."

    def _evidence_context(self):
        lines = []
        for _id, source, relation, target, confidence, created_at in self.memory.list_world_relationships()[:80]:
            lines.append(f"RELATION | {source} -> {relation} -> {target} | confidence={confidence / 100:.2f} | created_at={created_at}")
        for _id, entity_name, attribute, value, source_event, confidence, created_at, updated_at in self.memory.list_entity_states()[:80]:
            lines.append(f"STATE | {entity_name}.{attribute} = {value} | confidence={confidence / 100:.2f} | source_event={source_event}")
        for _id, name, entity_type, created_at in self.memory.list_entities()[:80]:
            lines.append(f"ENTITY | {name} | type={entity_type} | created_at={created_at}")
        for row in self.memory.list_knowledge_source_items(limit=50):
            _id, _source_id, source_name, category, statement, confidence, origin, evidence_json, created_at = row
            lines.append(f"SOURCE_ITEM | {category} | {statement} | confidence={confidence:.2f} | source={source_name} | origin={origin}")
        return lines[:220]

    def _build_reasoning_prompt(self, question, facts):
        return f"""
Você é o módulo de raciocínio estrutural da Athena.
Você NÃO grava memória diretamente.
Você NÃO inventa fatos.
Você usa apenas as evidências estruturadas como fatos de entrada.
Você pode usar o significado comum dos rótulos relacionais estruturados para inferências convencionais, mas deve citar as evidências usadas.
Você retorna SOMENTE JSON válido.

Decida se a pergunta exige inferência sobre as evidências.
Se exigir, gere conclusão rastreável.
Se a evidência não sustentar resposta, use should_reason=false ou baixa confiança.

Categorias:
- knowledge: fato diretamente sustentado
- belief: conclusão sustentada por evidências, mas não absoluta
- hypothesis: possibilidade plausível e incerta

Schema:
{{
  "should_reason": true,
  "category": "knowledge|belief|hypothesis",
  "statement": "string",
  "confidence": 0.0,
  "evidence": ["string"],
  "origin": "llm_structural_reasoning"
}}

Pergunta:
{question}

Evidências:
{json.dumps(facts, ensure_ascii=False, indent=2)}
""".strip()

    def _parse_json(self, raw_text):
        raw = raw_text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _normalize_conclusion(self, parsed):
        if not isinstance(parsed, dict):
            return None
        category = str(parsed.get("category") or "hypothesis").strip().lower()
        if category not in {"knowledge", "belief", "hypothesis"}:
            category = "hypothesis"
        statement = str(parsed.get("statement") or "").strip()
        if not statement:
            return None
        try:
            confidence = float(parsed.get("confidence", 0.50))
        except (TypeError, ValueError):
            confidence = 0.50
        if confidence > 1:
            confidence = confidence / 100
        confidence = max(0.0, min(1.0, confidence))
        return {
            "should_reason": bool(parsed.get("should_reason", True)),
            "category": category,
            "statement": statement,
            "confidence": confidence,
            "evidence": parsed.get("evidence") if isinstance(parsed.get("evidence"), list) else [],
            "origin": str(parsed.get("origin") or "llm_structural_reasoning").strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _format_conclusion(self, conclusion):
        statement = conclusion["statement"].strip()
        evidence = conclusion.get("evidence", [])[:5]
        if not evidence:
            return statement
        evidence_text = " ".join(str(item) for item in evidence[:2])
        if conclusion["category"] == "hypothesis":
            return f"Minha melhor hipótese é: {statement} Essa inferência vem destas evidências: {evidence_text}"
        return f"{statement} Essa é uma inferência baseada nas relações que conheço."

    def _row_to_line(self, row):
        _id, category, statement, confidence, evidence_json, origin, created_at = row
        return f"- {statement} | confiança {confidence:.2f} | origem {origin}"

    def _row_to_dict(self, row):
        _id, category, statement, confidence, evidence_json, origin, created_at = row
        try:
            evidence = json.loads(evidence_json)
        except json.JSONDecodeError:
            evidence = []
        return {
            "category": category,
            "statement": statement,
            "confidence": confidence,
            "evidence": evidence,
            "origin": origin,
            "created_at": created_at,
        }
