import json

from agency.json_utils import parse_json_object, clamp
from knowledge_sources.source_evaluator import SourceEvaluator


class KnowledgeIngestionEngine:
    """
    V11 generic knowledge ingestion.

    Sources are not domains. The engine receives structured intention/content,
    evaluates source reliability, asks the LLM to convert content into cognitive
    structure, and waits for Athena Core / human approval.
    """

    def __init__(self, memory, world_model, llm_provider, context_builder, logger=None, settings=None):
        self.memory = memory
        self.world_model = world_model
        self.llm_provider = llm_provider
        self.context_builder = context_builder
        self.logger = logger
        self.settings = settings
        self.source_evaluator = SourceEvaluator()

    def propose_from_intention(self, intention, original_text):
        request = intention.get("structured_request", {}) if isinstance(intention, dict) else {}
        content = self._first_non_empty(
            request.get("content"),
            request.get("source_content"),
            request.get("text"),
        )
        source_name = self._first_non_empty(request.get("source_name"), "fonte_fornecida_pelo_usuario")
        source_type = self._first_non_empty(request.get("source_type"), "generic_content")
        origin = self._first_non_empty(request.get("origin"), "user_supplied")
        metadata = request.get("metadata") if isinstance(request.get("metadata"), dict) else {"traceable": True}

        if not content and intention.get("intention_type") == "knowledge_source_request":
            content = original_text

        if not content:
            return None

        return self.propose(source_name, content, source_type=source_type, origin=origin, metadata=metadata)

    def propose(self, source_name, content, source_type="unknown", origin="user_supplied", metadata=None):
        evaluation = self.source_evaluator.evaluate(
            source_name=source_name,
            source_type=source_type,
            origin=origin,
            metadata=metadata or {},
            content=content,
        )

        extraction = self._llm_ingest(content, evaluation)
        if not extraction:
            if self.logger:
                self.logger.log("KNOWLEDGE_INGESTION", "LLM unavailable or invalid. Athena will not infer external knowledge by fallback.")
            return {
                "available": False,
                "evaluation": evaluation,
                "extraction": self._empty_extraction(),
                "decision": {"decision": "ask_context", "confidence": 0.0, "reason": "interpretação insegura"},
            }

        normalized = self._normalize_extraction(extraction, evaluation)
        normalized["source_content"] = content or ""
        decision = self._decide(normalized, evaluation)

        return {"available": True, "evaluation": evaluation, "extraction": normalized, "decision": decision}

    def apply(self, proposal):
        evaluation = proposal.get("evaluation", {})
        extraction = proposal.get("extraction", {})
        source_id = self.memory.save_knowledge_source(
            name=evaluation.get("source_name"),
            source_type=evaluation.get("source_type"),
            origin=evaluation.get("origin"),
            confidence=evaluation.get("confidence", 0.5),
            rationale=evaluation.get("rationale", ""),
            metadata=evaluation.get("metadata", {}),
        )
        saved_world = self.world_model.apply_extraction(extraction)
        self.memory.save_knowledge_ingestion(
            source_id=source_id,
            content=extraction.get("source_content", ""),
            summary=extraction.get("summary", ""),
            extracted=extraction,
            saved=saved_world,
        )
        saved_items = 0
        for item in extraction.get("knowledge", []):
            self._save_source_item(source_id, "knowledge", item, evaluation)
            saved_items += 1
        for item in extraction.get("beliefs", []):
            self._save_source_item(source_id, "belief", item, evaluation)
            saved_items += 1
        for item in extraction.get("hypotheses", []):
            self._save_source_item(source_id, "hypothesis", item, evaluation)
            saved_items += 1
        return {"source_id": source_id, "knowledge_items": saved_items, "world": saved_world}

    def format_preview(self, proposal):
        evaluation = proposal.get("evaluation", {})
        extraction = proposal.get("extraction", {})
        lines = [
            "Fonte avaliada de forma genérica:",
            f"- Nome: {evaluation.get('source_name')}",
            f"- Origem: {evaluation.get('origin')}",
            f"- Confiança da fonte: {evaluation.get('confidence', 0):.2f}",
            f"- Motivo: {evaluation.get('rationale')}",
        ]
        if extraction.get("summary"):
            lines.append(f"Resumo sugerido: {extraction.get('summary')}")
        for label, key in [("Conhecimentos", "knowledge"), ("Crenças", "beliefs"), ("Hipóteses", "hypotheses")]:
            items = extraction.get(key, [])
            if items:
                lines.append(f"{label} sugeridos:")
                for item in items[:5]:
                    lines.append(f"- {item.get('statement')} | confiança {item.get('confidence', 0):.2f}")
        world_preview = self.world_model.format_extraction_preview(extraction)
        if world_preview:
            lines.append("Estruturas do World Model sugeridas:")
            lines.append(world_preview)
        return "\n".join(lines)

    def sources_summary(self):
        sources = self.memory.list_knowledge_sources()
        if not sources:
            return "Ainda não estudei fontes externas registradas."
        lines = ["Fontes de conhecimento que já avaliei:"]
        for source in sources[:20]:
            _id, name, source_type, origin, confidence, rationale, _metadata, created_at = source
            lines.append(f"- {name} | tipo={source_type} | origem={origin} | confiança={confidence:.2f} | {created_at}")
            if rationale:
                lines.append(f"  motivo: {rationale}")
        return "\n".join(lines)

    def _llm_ingest(self, content, evaluation):
        if not self.llm_provider:
            return None
        prompt = self._build_prompt(content, evaluation)
        try:
            result = self.llm_provider.generate(prompt)
            if not result.available or not result.text:
                return None
            return parse_json_object(result.text)
        except Exception as error:
            if self.logger:
                self.logger.log("KNOWLEDGE_INGESTION_ERROR", str(error))
            return None

    def _build_prompt(self, content, evaluation):
        return f"""
Você é o módulo de ingestão estrutural de conhecimento da Athena.
Você converte conteúdo genérico em conhecimento potencial.
Você NÃO grava memória.
Você NÃO responde ao usuário.
Você NÃO cria regras por domínio, fonte ou palavra.
Retorne SOMENTE JSON válido.

Schema:
{{
  "summary": "string",
  "knowledge": [{{"statement": "string", "confidence": 0.0, "evidence": ["string"]}}],
  "beliefs": [{{"statement": "string", "confidence": 0.0, "evidence": ["string"]}}],
  "hypotheses": [{{"statement": "string", "confidence": 0.0, "evidence": ["string"]}}],
  "entities": [],
  "relationships": [],
  "events": [],
  "states": [],
  "temporal_references": []
}}

Avaliação genérica da fonte:
{json.dumps(evaluation, ensure_ascii=False)}

Conteúdo:
{content}
""".strip()

    def _empty_extraction(self):
        return {
            "summary": "",
            "knowledge": [],
            "beliefs": [],
            "hypotheses": [],
            "entities": [],
            "relationships": [],
            "events": [],
            "states": [],
            "temporal_references": [],
        }

    def _normalize_extraction(self, extraction, evaluation):
        normalized = self._empty_extraction()
        if not isinstance(extraction, dict):
            return normalized
        normalized["summary"] = str(extraction.get("summary") or "").strip()
        for source_key, target_key in [("knowledge", "knowledge"), ("beliefs", "beliefs"), ("hypotheses", "hypotheses")]:
            for item in extraction.get(source_key, []):
                if not isinstance(item, dict):
                    continue
                statement = str(item.get("statement") or "").strip()
                if not statement:
                    continue
                normalized[target_key].append({
                    "statement": statement,
                    "confidence": clamp(item.get("confidence"), evaluation.get("confidence", 0.5)),
                    "evidence": item.get("evidence") if isinstance(item.get("evidence"), list) else [],
                })
        for key in ["entities", "relationships", "events", "states", "temporal_references"]:
            value = extraction.get(key)
            normalized[key] = value if isinstance(value, list) else []
        normalized["source"] = "knowledge_ingestion_llm"
        return normalized

    def _decide(self, extraction, evaluation):
        confidences = [evaluation.get("confidence", 0.5)]
        for key in ["knowledge", "beliefs", "hypotheses", "entities", "relationships", "events", "states"]:
            for item in extraction.get(key, []):
                if isinstance(item, dict):
                    confidences.append(clamp(item.get("confidence"), 0.5))
        minimum = min(confidences) if confidences else 0.0
        auto = self.settings and self.settings.get("autoIngestExternalKnowledge", False) and minimum >= 0.95
        if auto:
            return {"decision": "save", "confidence": minimum, "reason": "confiança alta e ingestão automática habilitada"}
        if minimum >= 0.60:
            return {"decision": "confirm", "confidence": minimum, "reason": "aprendizado externo requer aprovação humana"}
        return {"decision": "ask_context", "confidence": minimum, "reason": "confiança insuficiente"}

    def _save_source_item(self, source_id, category, item, evaluation):
        confidence = min(clamp(item.get("confidence"), 0.5), clamp(evaluation.get("confidence"), 0.5))
        self.memory.save_knowledge_source_item(
            source_id=source_id,
            category=category,
            statement=item.get("statement"),
            confidence=confidence,
            origin=evaluation.get("origin", "unknown"),
            evidence=item.get("evidence", []),
        )

    def _first_non_empty(self, *values):
        for value in values:
            if value:
                return str(value).strip()
        return ""
