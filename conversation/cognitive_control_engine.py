import unicodedata


class CognitiveControlEngine:
    """Local-first cognitive control for clear, low-risk route decisions.

    This engine does not extract domain knowledge and does not answer factual
    questions by itself. It only decides whether Athena can route a message to a
    local subsystem before asking the intent LLM.
    """

    QUESTION_OPENERS = {
        "quem",
        "que",
        "qual",
        "quais",
        "quando",
        "onde",
        "como",
        "porque",
        "por",
        "quanto",
        "quantos",
        "quantas",
    }

    def __init__(self, identity=None, settings=None):
        self.identity = identity or {}
        self.settings = settings

    def classify(self, user_input, pending_state=None):
        words = self._words(user_input)
        if not words:
            return None

        pending_route = self._pending_confirmation(words, pending_state)
        if pending_route:
            return pending_route

        for resolver in (
            self._unknown_recovery,
            self._identity_route,
            self._capability_route,
            self._error_query,
            self._external_tool_missing,
            self._teach_intent,
            self._entity_query,
            self._conversation_route,
            self._learning_candidate,
        ):
            route = resolver(user_input, words)
            if route:
                return route
        return None

    def _route_result(
        self,
        route,
        intent,
        target="",
        target_type="unknown",
        requires_memory=False,
        should_query_world_model=False,
        requires_tool=False,
        tool_name=None,
        structured_request=None,
        source="local_cognitive_control",
        should_learn=False,
    ):
        return {
            "route": route,
            "intent": intent,
            "target": target,
            "target_type": target_type,
            "summary": intent or route,
            "confidence": 0.99,
            "needs_clarification": False,
            "requires_memory": requires_memory,
            "requires_tool": requires_tool,
            "tool_name": tool_name,
            "should_learn": bool(should_learn),
            "should_use_llm_response": False,
            "should_query_world_model": should_query_world_model,
            "should_query_self_model": route in {"identity", "self_status"},
            "should_use_reasoning": False,
            "should_use_agency": False,
            "structured_request": structured_request or {},
            "relevance": {},
            "original_route": route,
            "source": source,
            "intent_interpretation_ms": 0,
            "intent_llm_calls": 0,
            "relevance_llm_calls": 0,
        }

    def _pending_confirmation(self, words, pending_state):
        pending_state = pending_state if isinstance(pending_state, dict) else {}
        if pending_state.get("pending_type", "none") == "none":
            return None
        text = " ".join(words)
        approvals = {
            "sim",
            "s",
            "yes",
            "y",
            "ok",
            "okay",
            "pode",
            "autorizo",
            "confirmo",
            "claro",
            "salvar",
            "salve",
            "guarde",
            "guardar",
            "sim pode",
            "pode salvar",
            "pode guardar",
        }
        rejections = {
            "nao",
            "n",
            "no",
            "negativo",
            "cancela",
            "cancelar",
            "rejeito",
            "nao salve",
            "nao salvar",
            "nao guarde",
            "ignora",
            "ignorar",
        }
        if text in approvals:
            return self._route_result(
                route="pending_confirmation",
                intent="approval",
                structured_request={"operation": "approval"},
                source="local_cognitive_pending_confirmation",
            )
        if text in rejections:
            return self._route_result(
                route="pending_confirmation",
                intent="rejection",
                structured_request={"operation": "rejection"},
                source="local_cognitive_pending_confirmation",
            )
        return None

    def _unknown_recovery(self, _user_input, words):
        if len(words) > 12:
            return None
        word_set = set(words)
        if (
            word_set & {"voce", "vc", "vce"}
            and word_set & {"o", "que", "oq", "oque", "qual"}
            and word_set & {"entendeu", "entender", "compreendeu", "compreender"}
            and word_set & {"nao", "n"}
        ):
            return self._route_result(
                route="system",
                intent="unknown_recovery",
                target="last_unknown",
                target_type="world",
                structured_request={"operation": "unknown_recovery"},
                source="local_cognitive_unknown_recovery",
            )
        return None

    def _identity_route(self, _user_input, words):
        if len(words) > 12:
            return None
        text = " ".join(words)
        athena_name = self._identity_word("name", "athena")
        creator = str(self.identity.get("creator") or "").strip()

        if "quem sou eu" in text or "quem eu sou" in text:
            return self._route_result(
                route="question_about_user",
                intent="user_identity",
                target=creator,
                target_type="user",
                requires_memory=True,
                should_query_world_model=True,
                structured_request={"operation": "user_identity"},
                source="local_cognitive_user_identity",
            )

        if "quem te criou" in text or "quem criou voce" in text or f"quem criou {athena_name}" in text:
            return self._route_result(
                route="identity",
                intent="creator_query",
                target=creator,
                target_type="user",
                structured_request={"operation": "creator_query"},
                source="local_cognitive_creator_query",
            )

        if "quem e voce" in text or "quem eh voce" in text or f"quem e {athena_name}" in text or f"quem eh {athena_name}" in text:
            return self._route_result(
                route="identity",
                intent="self_identity",
                target=self.identity.get("name", "Athena"),
                target_type="self",
                structured_request={"operation": "self_identity"},
                source="local_cognitive_self_identity",
            )
        return None

    def _capability_route(self, _user_input, words):
        if len(words) > 28:
            return None
        word_set = set(words)
        capability_terms = {"capacidade", "capacidades", "habilidade", "habilidades", "recursos"}
        action_terms = {"fazer", "faz", "consegue", "pode", "ajudar", "serve"}
        subject_terms = {"voce", "vc", "vce", self._identity_word("name", "athena")}
        query_terms = {"o", "que", "oq", "oque", "qual", "quais", "como"}
        asks_capability = bool(word_set & capability_terms)
        asks_action = bool(word_set & subject_terms and word_set & action_terms and word_set & query_terms)
        if not asks_capability and not asks_action:
            return None
        structured_request = {"operation": "capability_query"}
        if self._has_positive_day_context(words):
            structured_request["positive_day_context"] = True
        return self._route_result(
            route="capability",
            intent="capability_query",
            target=self.identity.get("name", "Athena"),
            target_type="self",
            structured_request=structured_request,
            source="local_cognitive_capability_query",
        )

    def _error_query(self, _user_input, words):
        if len(words) > 12:
            return None
        word_set = set(words)
        if not (word_set & {"erro", "error", "falha"}):
            return None
        if word_set & {"ultimo", "ultima", "aconteceu"} or words[:2] == ["qual", "foi"]:
            return self._route_result(
                route="error_query",
                intent="error_query",
                target="last_error",
                target_type="world",
                structured_request={"operation": "last_error"},
                source="local_cognitive_error_query",
            )
        return None

    def _external_tool_missing(self, _user_input, words):
        if len(words) > 20:
            return None
        if not self._looks_like_question(words):
            return None
        word_set = set(words)
        current_terms = {"hoje", "agora", "atual", "atuais", "real", "previsao", "cotacao", "manchetes"}
        if not (word_set & current_terms):
            return None
        target = "informacao externa atual"
        return self._route_result(
            route="external_information",
            intent="external_information",
            target=target,
            target_type="tool",
            requires_tool=True,
            tool_name=target,
            structured_request={"operation": "external_tool_missing"},
            source="local_cognitive_external_tool_missing",
        )

    def _teach_intent(self, _user_input, words):
        if len(words) > 18:
            return None
        word_set = set(words)
        teach_terms = {"ensinar", "ensino", "explicar", "explico", "contar", "conto"}
        intent_terms = {"posso", "quero", "vou", "deixa", "deixe"}
        if word_set & teach_terms and word_set & intent_terms:
            return self._route_result(
                route="teach_intent",
                intent="teach_intent",
                target=self.identity.get("name", "Athena"),
                target_type="self",
                structured_request={"operation": "teach_intent"},
                source="local_cognitive_teach_intent",
            )
        return None

    def _entity_query(self, _user_input, words):
        if len(words) > 28:
            return None
        if not self._looks_like_question(words):
            return None
        target = self._extract_entity_target(words)
        if not target:
            return None
        return self._route_result(
            route="world_query",
            intent="entity_query",
            target=target,
            target_type="entity",
            requires_memory=True,
            should_query_world_model=True,
            source="local_cognitive_entity_query",
        )

    def _learning_candidate(self, user_input, words):
        if len(words) > 32 or self._looks_like_question(words):
            return None
        if self._looks_like_copula_assertion(words) or self._looks_like_preference_assertion(words):
            target, target_type = self._learning_target(user_input, words)
            return self._route_result(
                route="learning",
                intent="learning_candidate",
                target=target,
                target_type=target_type,
                requires_memory=True,
                should_query_world_model=False,
                structured_request={"operation": "learning_candidate"},
                source="local_cognitive_learning_candidate",
                should_learn=True,
            )
        return None

    def _conversation_route(self, _user_input, words):
        if len(words) > 12 or self._looks_like_question(words):
            return None
        word_set = set(words)
        greetings = {"oi", "ola", "opa", "eai", "bom", "boa"}
        small_talk = {"bem", "tranquilo", "tranquila", "tudo", "sim"}
        if word_set & greetings and word_set & small_talk:
            return self._route_result(
                route="small_talk",
                intent="small_talk",
                source="local_cognitive_conversation",
            )
        if word_set & greetings:
            return self._route_result(
                route="greeting",
                intent="greeting",
                source="local_cognitive_conversation",
            )
        return None

    def _extract_entity_target(self, words):
        for index in range(len(words) - 2):
            if words[index] == "quem" and words[index + 1] in {"e", "eh"}:
                return self._target_from_words(words[index + 2 :])

        prefix = ["o", "que", "voce", "sabe", "sobre"]
        for index in range(len(words) - len(prefix)):
            if words[index : index + len(prefix)] == prefix:
                return self._target_from_words(words[index + len(prefix) :])
        return ""

    def _target_from_words(self, words):
        ignored = {"a", "o", "as", "os", "um", "uma", "uns", "umas", "sobre"}
        stop_words = {"por", "favor", "agora", "hoje"}
        target_words = []
        for word in words:
            if word in stop_words:
                break
            if word in ignored:
                continue
            target_words.append(word)
        target = " ".join(target_words).strip()
        reserved = {
            "voce",
            "voces",
            "eu",
            self._identity_word("name", "athena"),
            self._identity_word("creator", ""),
        }
        if not target or target in reserved:
            return ""
        return self._display_target(target)

    def _learning_target(self, user_input, words):
        self_terms = {"voce", "vc", "vce", self._identity_word("name", "athena")}
        if set(words) & self_terms:
            return self.identity.get("name", "Athena"), "self"

        for copula in ("e", "eh"):
            if copula in words:
                index = words.index(copula)
                left = words[:index]
                right = words[index + 1 :]
                if left and left[0] in {"meu", "minha", "meus", "minhas"} and right:
                    return self._display_target(" ".join(right[:3])), "entity"
                if left:
                    return self._display_target(" ".join(left[:3])), "entity"

        raw = str(user_input or "").strip()
        return raw[:80], "unknown"

    def _looks_like_copula_assertion(self, words):
        if not any(copula in words for copula in {"e", "eh"}):
            return False
        if words[0] in self.QUESTION_OPENERS:
            return False
        for copula in ("e", "eh"):
            if copula in words:
                index = words.index(copula)
                return bool(words[:index] and words[index + 1 :])
        return False

    def _looks_like_preference_assertion(self, words):
        if len(words) < 4:
            return False
        return words[:3] == ["eu", "gosto", "de"] or (len(words) >= 4 and words[1:3] == ["gosta", "de"])

    def _looks_like_question(self, words):
        if not words:
            return False
        if words[0] in self.QUESTION_OPENERS:
            return True
        return any(words[index] == "quem" and index + 1 < len(words) and words[index + 1] in {"e", "eh"} for index in range(len(words)))

    def _has_positive_day_context(self, words):
        word_set = set(words)
        day_terms = {"dia", "manha", "tarde", "noite"}
        positive_terms = {"bom", "boa", "otimo", "otima", "legal", "feliz", "excelente", "tranquilo", "tranquila"}
        return bool(word_set & day_terms and word_set & positive_terms)

    def _words(self, text):
        normalized = self._normalize(text)
        chars = []
        for char in normalized:
            chars.append(char if char.isalnum() else " ")
        return "".join(chars).split()

    def _normalize(self, text):
        normalized = unicodedata.normalize("NFKD", str(text or "").strip().lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return " ".join(normalized.split())

    def _identity_word(self, key, default):
        return self._normalize(self.identity.get(key) or default)

    def _display_target(self, target):
        words = [word for word in str(target or "").split() if word]
        return " ".join(word.capitalize() if word.isalpha() else word for word in words)
