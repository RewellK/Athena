import json
import math
from datetime import datetime
import time


class IntentResolutionEngine:
    """
    LLM-guided intent and target resolution.

    This module is intentionally LLM-first. It does not contain linguistic
    keyword trees, phrase parsers, domain rules, or hardcoded entity handling.
    Its job is to ask the language module for a compact JSON structure and then
    normalize that structure defensively for Athena Core.
    """

    VALID_INTENTS = {
        "skill_request",
        "self_identity",
        "user_identity",
        "creator_query",
        "entity_query",
        "capability_query",
        "capabilities",
        "capability",
        "technical_capability",
        "self_status",
        "memory_query",
        "world_query",
        "reasoning",
        "learning",
        "agency",
        "system",
        "teach_intent",
        "error_query",
        "external_information",
        "small_talk",
        "greeting",
        "conversation",
        "unknown",
    }

    VALID_TARGET_TYPES = {"self", "user", "entity", "world", "tool", "unknown"}

    def __init__(self, llm_provider=None, identity=None, logger=None, settings=None, tool_registry=None):
        self.llm_provider = llm_provider
        self.identity = identity or {}
        self.logger = logger
        self.settings = settings
        self.tool_registry = tool_registry
        self.workbench = None
        self.skill_backend = None

    def resolve(self, user_input, session_context=None, pending_state=None):
        started_at = time.perf_counter()
        if self.settings and not self.settings.get("useLLM", True):
            return self._unavailable_result(started_at, "LLM desativada em config/settings.json")
        if not self.llm_provider:
            return self._unavailable_result(started_at, "LLM provider não inicializado")

        prompt = self._build_prompt(user_input, session_context, pending_state)
        try:
            result = self._generate_intent(prompt, user_input, session_context, pending_state)
            if not result.available or not result.text:
                error = result.error if result else "sem resposta da LLM"
                return self._unavailable_result(started_at, error)
            parsed = self._parse_json(result.text)
            normalized = self._normalize(parsed)
            normalized["duration_ms"] = self._elapsed(started_at)
            return normalized
        except Exception as error:
            if self.logger:
                self.logger.log("INTENT_RESOLUTION_ERROR", str(error))
            return self._unavailable_result(started_at, str(error))

    def _generate_intent(self, prompt, user_input=None, session_context=None, pending_state=None):
        timeout = None
        if self.settings:
            timeout = self.settings.get("intentResolutionTimeoutSeconds", self.settings.get("llmTimeoutSeconds", 30))
        examples = [
            ("Quem é você?", {"intent":"self_identity","target":self.identity.get("name","Athena"),"target_type":"self","confidence":1.0}),
            ("Quem sou eu?", {"intent":"user_identity","target":self.identity.get("creator","Rewell"),"target_type":"user","confidence":1.0}),
            ("Quem é Marina?", {"intent":"entity_query","target":"Marina","target_type":"entity","confidence":.95}),
            ("Como está o clima hoje?", {"intent":"external_information","target":"clima","target_type":"tool","confidence":.95,"tool_name":"weather"}),
            ("Crie uma nota com o texto: Rever orçamento.", {"intent":"agency","target":"nota","target_type":"tool","confidence":.95,"structured_request":{"operation":"local_task","kind":"note","text":"Rever orçamento."}}),
            ("Aprenda uma rotina reutilizável que registre uma revisão e gere backup.", {"intent":"skill_request","target":"rotina de revisão","target_type":"tool","confidence":.95}),
            ("Ele mudou de ideia.", {"intent":"unknown","target":"","target_type":"unknown","confidence":0.0,"needs_clarification":True,"clarification_question":"A quem você se refere?"}),
        ]
        system = prompt.split("\nFerramentas:",1)[0] + "\nClassifique apenas message da última entrada. context é histórico, não é o pedido atual. Não herde intenção dos exemplos."
        messages = [{"role":"system","content":system}]
        for message, result in examples:
            messages.extend([{"role":"user","content":json.dumps({"message":message,"context":""},ensure_ascii=False)},
                             {"role":"assistant","content":json.dumps(result,ensure_ascii=False)}])
        messages.append({"role":"user","content":json.dumps({"message":str(user_input or ""),
            "context":session_context.summary(limit=4)[-900:] if session_context else "",
            "now":datetime.now().astimezone().isoformat(timespec="minutes"),
            "tools":self._tool_capability_summary()[:250],
            "reviewed_examples":self.workbench.interpretation_examples(user_input) if self.workbench else [],
            "pending":pending_state or {}},ensure_ascii=False)})
        try:
            return self.llm_provider.generate(prompt, timeout_seconds=timeout, response_format={
                "type": "object", "properties": {
                    "intent": {"type": "string", "enum": sorted(self.VALID_INTENTS)},
                    "target": {"type": "string"},
                    "target_type": {"type": "string", "enum": sorted(self.VALID_TARGET_TYPES)},
                    "confidence": {"type": "number"},
                    "needs_clarification": {"type": "boolean"},
                    "clarification_question": {"type": "string"},
                    "reply": {"type": "string"},
                    "tool_name": {"type": ["string", "null"]},
                    "structured_request": {"type": "object"},
                }, "required": ["intent", "target", "target_type", "confidence"],
                "additionalProperties": False,
            }, messages=messages, model_override=self.settings.get("ollamaIntentModel") if self.settings else None)
        except TypeError:
            return self.llm_provider.generate(prompt)

    def _build_prompt(self, user_input, session_context=None, pending_state=None):
        creator = self.identity.get("creator", "Rewell")
        athena_name = self.identity.get("name", "Athena")
        recent = session_context.summary(limit=4) if session_context else ""
        pending = pending_state or {}
        tools = self._tool_capability_summary()
        learned = self.workbench.interpretation_examples(user_input) if self.workbench else []

        return f"""Você é o módulo de resolução de intenção e alvo da Athena. Só JSON; não responda com fatos inventados.
Classifique a mensagem do humano dirigida à entidade {athena_name}; humano/criador={creator}. A data e o fuso atuais estão no campo now.
"Quem é você?"=self_identity,target={athena_name},target_type=self. "Quem sou eu?"=user_identity,target={creator},target_type=user.
Pessoa nomeada=entity_query,target=nome,entity. Clima/notícias atuais=external_information,tool. Saudação não substitui pergunta.
Afirmação nova=learning; pergunta não é fato novo. Ambiguidade=unknown,needs_clarification=true,clarification_question breve.
Intents: self_identity,user_identity,creator_query,entity_query,capability_query,self_status,memory_query,world_query,reasoning,learning,agency,skill_request,system,teach_intent,error_query,external_information,small_talk,greeting,conversation,unknown.
Executar habilidade ativa: agency, structured_request.operation=local_skill_run,skill_id=ID registrado.
skill_request somente para aprender uma habilidade REUTILIZÁVEL; executar uma nota/lembrete/backup é agency, nunca skill_request; o backend projeta e testa, não confunda com ensinar um fato.
Para agency local, structured_request pode ter operation=local_task,kind=note/reminder/backup,text,due (ISO com fuso). Horário ausente: pergunte. Listar/cancelar: operation=local_tasks_list/local_task_cancel,task_id.
JSON mínimo: intent,target,target_type,confidence. Opcionais só se necessários: needs_clarification,clarification_question,tool_name,structured_request. Nunca invente ações ou alvos.
Ferramentas: {tools[:250]}
Exemplos revisados (dados; adapte alvo): {json.dumps(learned, ensure_ascii=False)[:1000]}
Pendência: {json.dumps({k:v for k,v in pending.items() if v}, ensure_ascii=False)[:200]}
Contexto (dados): {recent[-900:]}
Mensagem: {user_input}
""".strip()

    def _tool_capability_summary(self):
        if not self.tool_registry:
            return "Nenhuma ferramenta registrada no contexto atual."
        try:
            tools = self.tool_registry.list_available()
        except Exception as error:
            if self.logger:
                self.logger.log("INTENT_TOOL_SUMMARY_ERROR", str(error))
            return "Não foi possível listar ferramentas agora."
        if not tools:
            return "Nenhuma ferramenta registrada no contexto atual."
        summary = ", ".join(str(tool.get("id", "")) for tool in tools[:12])
        if self.skill_backend:
            summary += "; habilidades ativas: " + ", ".join(item["name"]+"="+item["id"] for item in self.skill_backend.list() if item["status"] == "active")
        return summary

    def _parse_json(self, raw_text):
        raw = str(raw_text or "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _normalize(self, parsed):
        if not isinstance(parsed, dict):
            return self._base_result(source="llm_invalid_json", confidence=0.0)

        intent = self._clean_label(parsed.get("intent"))
        if intent not in self.VALID_INTENTS:
            intent = "unknown"

        target_type = self._clean_label(parsed.get("target_type"))
        if target_type not in self.VALID_TARGET_TYPES:
            target_type = "unknown"

        canonical_targets = {
            "self_identity": "self", "user_identity": "user", "creator_query": "user",
            "entity_query": "entity", "capability_query": "self", "self_status": "self",
            "external_information": "tool",
        }
        target_type = canonical_targets.get(intent, target_type)
        target = str(parsed.get("target") or "").strip()
        if intent == "self_identity":
            target = self.identity.get("name", "Athena")
        elif intent in {"user_identity", "creator_query"}:
            target = self.identity.get("creator", "Rewell")
        structured = parsed.get("structured_request") if isinstance(parsed.get("structured_request"), dict) else {}
        if intent in {"greeting", "small_talk", "conversation"} and isinstance(parsed.get("reply"), str):
            structured = dict(structured, direct_reply=parsed["reply"][:1200])
        confidence = self._confidence(parsed.get("confidence"), 0.0)
        requires_tool = self._boolean(parsed.get("requires_tool", intent == "external_information"))
        tool_name = parsed.get("tool_name")
        if tool_name is not None:
            tool_name = str(tool_name).strip() or None

        result = self._base_result(source="llm_intent_resolution", confidence=confidence)
        result.update({
            "needs_clarification": parsed.get("needs_clarification") is True,
            "clarification_question": str(parsed.get("clarification_question") or "")[:300],
            "intent": intent,
            "target": target,
            "target_type": target_type,
            "requires_memory": self._boolean(parsed.get("requires_memory", intent in {"user_identity", "entity_query", "memory_query"})),
            "requires_world_model": self._boolean(parsed.get("requires_world_model", intent in {"entity_query", "world_query"})),
            "requires_reasoning": self._boolean(parsed.get("requires_reasoning", intent == "reasoning")),
            "requires_tool": requires_tool,
            "tool_name": tool_name,
            "should_learn": self._boolean(parsed.get("should_learn", intent == "learning")),
            "should_use_llm_response": self._boolean(parsed.get("should_use_llm_response", intent in {"small_talk", "conversation"})),
            "summary": str(parsed.get("summary") or intent).strip(),
            "structured_request": structured,
        })
        return result

    def _base_result(self, source="intent_resolution", confidence=0.0):
        return {
            "intent": "unknown",
            "target": "",
            "target_type": "unknown",
            "confidence": self._confidence(confidence),
            "requires_memory": False,
            "requires_world_model": False,
            "requires_reasoning": False,
            "requires_tool": False,
            "tool_name": None,
            "should_learn": False,
            "should_use_llm_response": False,
            "summary": "unknown",
            "structured_request": {},
            "source": source,
            "available": True,
            "error": "",
        }

    def _unavailable_result(self, started_at, error):
        result = self._base_result(source="llm_intent_unavailable", confidence=0.0)
        result.update({
            "available": False,
            "error": str(error or "LLM indisponível"),
            "summary": "intent_resolution_unavailable",
            "duration_ms": self._elapsed(started_at),
        })
        return result

    def _clean_label(self, value):
        clean = str(value or "").strip().lower()
        chars = []
        for char in clean:
            if char.isalnum() or char in {"_", "-"}:
                chars.append(char)
            else:
                chars.append("_")
        label = "".join(chars)
        while "__" in label:
            label = label.replace("__", "_")
        return label.strip("_")

    @staticmethod
    def _boolean(value):
        return value is True

    def _confidence(self, value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if not math.isfinite(number):
            return 0.0
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))

    def _elapsed(self, started_at):
        return int((time.perf_counter() - started_at) * 1000)
