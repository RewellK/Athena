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

    def classify(self, user_input, pending_state=None, session_context=None):
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
            self._admin_route,
            self._error_query,
            self._external_tool_missing,
            self._teach_intent,
            self._entity_query,
            self._conversation_route,
            self._learning_candidate,
        ):
            route = resolver(user_input, words, session_context)
            if route:
                return route
        return None

    def _admin_route(self, _user_input, words, session_context=None):
        if len(words) > 60:
            return None
        word_set = set(words)
        text = " ".join(words)

        if "v13" in word_set and word_set & {"pronta", "preparada", "ready"}:
            operation = "v12_9_readiness" if "pre" in word_set or "pre" in text or "v13" in word_set else "v12_readiness"
            return self._route_result(
                route="memory_query",
                intent=operation,
                target="v13_readiness",
                target_type="system",
                structured_request={"operation": operation},
                source="local_cognitive_v12_readiness",
            )

        location_admin = self._location_admin_route(_user_input, words, word_set)
        if location_admin:
            return location_admin

        learning_admin = self._learning_admin_route(words, word_set)
        if learning_admin:
            return learning_admin

        expansion_admin = self._expansion_admin_route(words, word_set)
        if expansion_admin:
            return expansion_admin

        if word_set & {"fonte", "fontes"}:
            operation = "pending_sources" if word_set & {"pendente", "pendentes", "validacao", "validação"} else "source_admin"
            return self._route_result(
                route="memory_query",
                intent=operation,
                target="sources",
                target_type="system",
                structured_request={"operation": operation},
                source="local_cognitive_source_admin",
            )

        if "pesquisando" in word_set or (word_set & {"estrategia", "estrategias"} and word_set & {"pesquisa", "pesquisar"}):
            return self._route_result(
                route="memory_query",
                intent="research_admin",
                target="research_strategies",
                target_type="system",
                structured_request={"operation": "research_admin"},
                source="local_cognitive_research_admin",
            )

        if word_set & {"memoria", "memorias", "lembra", "lembrar"}:
            if "sobre" in word_set:
                target = self._extract_memory_target(words, session_context=session_context)
                return self._route_result(
                    route="memory_query",
                    intent="memory_admin",
                    target=target,
                    target_type="entity" if target else "unknown",
                    requires_memory=True,
                    should_query_world_model=bool(target),
                    structured_request={"operation": "memory_about_entity", "target": target},
                    source="local_cognitive_memory_admin",
                )
            operation = "pending_memories"
            if word_set & {"importante", "importantes"}:
                operation = "important_memories"
            elif word_set & {"velha", "velhas", "velho", "velhos", "stale", "vencida", "vencidas"}:
                operation = "stale_memories"
            elif word_set & {"melhoria", "melhorias", "melhorar"}:
                operation = "improvement_memories"
            return self._route_result(
                route="memory_query",
                intent=operation,
                target="memory",
                target_type="system",
                requires_memory=True,
                structured_request={"operation": operation},
                source="local_cognitive_memory_admin",
            )

        if "confirmar" in word_set and word_set & {"comigo", "pendente", "pendentes"}:
            return self._route_result(
                route="memory_query",
                intent="pending_memories",
                target="memory",
                target_type="system",
                requires_memory=True,
                structured_request={"operation": "pending_memories"},
                source="local_cognitive_memory_admin",
            )

        if text in {"tem algo que voce precisa melhorar", "o que voce precisa melhorar"}:
            return self._route_result(
                route="memory_query",
                intent="improvement_memories",
                target="reflection",
                target_type="system",
                structured_request={"operation": "improvement_memories"},
                source="local_cognitive_improvement_admin",
            )
        return None

    def _location_admin_route(self, user_input, words, word_set):
        location_terms = {"localizacao", "localização", "cidade", "local"}
        if not (word_set & location_terms):
            return None
        text = " ".join(words)
        operation = ""
        if word_set & {"apague", "apagar", "delete", "remova", "remover"}:
            operation = "clear_location"
        elif ("nao" in word_set or "não" in word_set) and word_set & {"salvar", "salve", "guardar", "guarde"}:
            operation = "deny_location"
        elif word_set & {"porque", "por", "precisa", "preciso"} and word_set & location_terms:
            operation = "why_location"
        elif word_set & {"qual", "quais", "tem", "salva", "salvo", "mostre"}:
            operation = "location_status"
        elif "so" in word_set and "agora" in word_set:
            operation = "one_time_location"
        elif (
            "minha localizacao e" in text
            or "minha localizacao eh" in text
            or "minha cidade e" in text
            or "minha cidade eh" in text
            or ("use" in word_set and word_set & {"padrao", "padrão"})
            or ("configure" in word_set and word_set & {"cidade", "localizacao", "localização"})
        ):
            operation = "set_default_location"
        if not operation:
            return None
        return self._route_result(
            route="memory_query",
            intent=operation,
            target="location",
            target_type="system",
            structured_request={"operation": operation, "raw_location_text": user_input},
            source="local_cognitive_location_admin",
        )

    def _expansion_admin_route(self, words, word_set):
        create_terms = {"crie", "criar", "cria", "proponha", "propor", "registre", "registrar"}
        if word_set & {"melhorar", "melhoria", "melhorias"} and not (word_set & create_terms):
            return None
        module_terms = {"modulo", "modulos", "módulo", "módulos", "orgao", "orgaos", "órgão", "órgãos"}
        proposal_terms = {"proposta", "propostas"}
        gap_terms = {"lacuna", "lacunas", "falta", "precisa", "necessario", "necessário"}
        if not (word_set & module_terms or word_set & proposal_terms or word_set & gap_terms or word_set & create_terms):
            return None

        operation = ""
        identifier = ""
        if word_set & create_terms and (word_set & proposal_terms or word_set & module_terms or word_set & {"melhoria", "melhorias"}):
            operation = "create_module_proposal"
        elif word_set & {"aprovar", "aprova", "aprove"} and word_set & proposal_terms:
            operation = "approve_module_proposal"
            identifier = words[-1] if words else ""
        elif word_set & {"rejeitar", "rejeita", "rejeite"} and word_set & proposal_terms:
            operation = "reject_module_proposal"
            identifier = words[-1] if words else ""
        elif word_set & proposal_terms or word_set & module_terms:
            operation = "module_proposals"
        elif word_set & gap_terms:
            operation = "capability_gaps"
        if not operation:
            return None
        return self._route_result(
            route="memory_query",
            intent=operation,
            target="capability_expansion",
            target_type="system",
            structured_request={"operation": operation, "identifier": identifier},
            source="local_cognitive_capability_gap_admin",
        )

    def _learning_admin_route(self, words, word_set):
        has_training = word_set & {"treino", "treinamento", "exemplo", "exemplos"}
        has_pattern = word_set & {"padrao", "padroes", "padrão", "padrões"}
        has_insight = word_set & {"insight", "insights"}
        has_teacher = ("llm" in word_set or "qwen" in word_set or "professora" in word_set) and word_set & {"ensinou", "ensinar", "insights"}
        has_last_learning_question = word_set & {"aprendeu", "aprendi"} and word_set & {"ultima", "resposta"}
        has_correction = word_set & {"corrige", "corrigir", "correcao", "correção"}

        operation = ""
        identifier = ""
        if has_correction:
            operation = "create_training_example_from_correction"
        elif word_set & {"aprovar", "aprova", "aprove", "converter", "converta"}:
            identifier = words[-1] if words else ""
            if has_insight:
                operation = "approve_self_insight"
            elif has_training:
                operation = "approve_training_example"
        elif word_set & {"rejeitar", "rejeita", "rejeite"}:
            identifier = words[-1] if words else ""
            if has_insight:
                operation = "reject_self_insight"
            elif has_training:
                operation = "reject_training_example"
        elif has_training:
            operation = "pending_training_examples"
        elif has_pattern:
            operation = "learned_linguistic_patterns"
        elif has_insight:
            operation = "pending_self_insights"
        elif has_teacher:
            operation = "llm_teacher_insights"
        elif has_last_learning_question:
            operation = "pending_self_insights"
        elif "llm" in word_set and word_set & {"consegue", "fazer", "sem"}:
            operation = "local_patterns_without_llm"
        elif "llm" in word_set and word_set & {"dependem", "depende", "dependencia", "dependência"}:
            operation = "llm_dependencies"

        if not operation:
            return None
        return self._route_result(
            route="memory_query",
            intent=operation,
            target="learning",
            target_type="system",
            structured_request={"operation": operation, "identifier": identifier},
            source="local_cognitive_learning_admin",
        )

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

    def _unknown_recovery(self, _user_input, words, _session_context=None):
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

    def _identity_route(self, _user_input, words, _session_context=None):
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
            operation = "relationship_to_user" if ("pra mim" in text or "para mim" in text) else "self_identity"
            return self._route_result(
                route="identity",
                intent="self_identity",
                target=self.identity.get("name", "Athena"),
                target_type="self",
                structured_request={"operation": operation},
                source="local_cognitive_self_identity",
            )
        return None

    def _capability_route(self, _user_input, words, _session_context=None):
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
        if "nao" in word_set and (word_set & {"consegue", "pode", "faz", "fazer"} or "ainda" in word_set):
            structured_request["limitations_query"] = True
        return self._route_result(
            route="capability",
            intent="capability_query",
            target=self.identity.get("name", "Athena"),
            target_type="self",
            structured_request=structured_request,
            source="local_cognitive_capability_query",
        )

    def _error_query(self, _user_input, words, _session_context=None):
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

    def _external_tool_missing(self, _user_input, words, _session_context=None):
        if len(words) > 20:
            return None
        word_set = set(words)
        external_terms = {
            "hoje",
            "agora",
            "atual",
            "atuais",
            "real",
            "previsao",
            "cotacao",
            "manchetes",
            "noticia",
            "noticias",
            "clima",
            "tempo",
            "temperatura",
            "chuva",
            "preco",
            "valor",
            "custa",
            "custaria",
            "fipe",
            "carro",
            "veiculo",
            "veiculos",
            "jurisprudencia",
            "juridico",
            "juridica",
        }
        if not (word_set & external_terms):
            return None
        price_terms = {"preco", "valor", "custa", "custaria", "cotacao"}
        research_verbs = {"busque", "buscar", "pesquise", "pesquisar", "consulte", "consulta", "procure", "procurar"}
        if not self._looks_like_question(words) and not (word_set & price_terms) and not (word_set & research_verbs):
            return None
        domain = self._external_domain(words)
        target = self._external_domain_label(domain)
        return self._route_result(
            route="external_information",
            intent="external_information",
            target=target,
            target_type="tool",
            requires_tool=True,
            tool_name=target,
            structured_request={"operation": "external_tool_missing", "domain": domain},
            source="local_cognitive_external_tool_missing",
        )

    def _teach_intent(self, _user_input, words, _session_context=None):
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

    def _entity_query(self, _user_input, words, session_context=None):
        if len(words) > 34:
            return None
        target = self._extract_entity_target(words, session_context=session_context)
        if not target:
            return None
        operation = "user_relation_query" if self._is_user_relation_target(target) else "entity_query"
        structured_request = {"operation": operation}
        if self._wants_technical_output(words):
            structured_request["mode"] = "technical"
        return self._route_result(
            route="world_query",
            intent="entity_query",
            target=target,
            target_type="entity",
            requires_memory=True,
            should_query_world_model=True,
            structured_request=structured_request,
            source="local_cognitive_entity_query",
        )

    def _learning_candidate(self, user_input, words, session_context=None):
        if len(words) > 32 or self._looks_like_question(words):
            return None
        if self._looks_like_copula_assertion(words) or self._looks_like_preference_assertion(words):
            target, target_type = self._learning_target(user_input, words, session_context=session_context)
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

    def _conversation_route(self, _user_input, words, _session_context=None):
        if len(words) > 12 or self._looks_like_question(words):
            return None
        text = " ".join(words)
        word_set = set(words)
        acknowledgements = {"sim", "ok", "okay", "claro", "beleza", "certo", "perfeito", "entendi"}
        if text in acknowledgements:
            return self._route_result(
                route="conversation",
                intent="conversation",
                structured_request={"operation": "acknowledgement"},
                source="local_cognitive_acknowledgement",
            )
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

    def _extract_entity_target(self, words, session_context=None):
        for index in range(len(words) - 2):
            if words[index] == "quem" and words[index + 1] in {"e", "eh"}:
                return self._resolve_contextual_target(self._target_from_words(words[index + 2 :]), session_context)

        for index in range(len(words) - 3):
            if words[index] in {"sabe", "sabia"} and words[index + 1] in {"quem", "que"} and words[index + 2] in {"e", "eh"}:
                return self._resolve_contextual_target(self._target_from_words(words[index + 3 :]), session_context)

        for index, word in enumerate(words):
            if word == "sobre" and index + 1 < len(words):
                return self._resolve_contextual_target(self._target_from_words(words[index + 1 :]), session_context)

        for index in range(len(words) - 2):
            if words[index] in {"fala", "fale"} and words[index + 1] in {"dele", "dela", "nele", "nela"}:
                return self._resolve_contextual_target(words[index + 1], session_context)

        if words[:2] in (["me", "fala"], ["me", "fale"]) and len(words) >= 3:
            return self._resolve_contextual_target(self._target_from_words(words[2:]), session_context)
        return ""

    def _extract_memory_target(self, words, session_context=None):
        if "sobre" not in words:
            return ""
        index = words.index("sobre")
        target = self._target_from_words(words[index + 1 :])
        if target.lower() in {"mim", "me"}:
            return self.identity.get("creator", "")
        return self._resolve_contextual_target(target, session_context)

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

    def _learning_target(self, user_input, words, session_context=None):
        self_terms = {"voce", "vc", "vce", self._identity_word("name", "athena")}
        if set(words) & self_terms:
            return self.identity.get("name", "Athena"), "self"
        if words and words[0] in {"ele", "ela"}:
            resolved = self._resolve_contextual_target(words[0], session_context)
            if resolved:
                return resolved, "entity"

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
        if words[0] == "eu" and "gosto" in words:
            return True
        return words[:3] == ["eu", "gosto", "de"] or (len(words) >= 4 and words[1:3] == ["gosta", "de"])

    def _looks_like_question(self, words):
        if not words:
            return False
        if words[0] in self.QUESTION_OPENERS:
            return True
        if any(words[index] == "quem" and index + 1 < len(words) and words[index + 1] in {"e", "eh"} for index in range(len(words))):
            return True
        return self._looks_like_entity_information_request(words)

    def _external_domain(self, words):
        word_set = set(words)
        if word_set & {"clima", "tempo", "previsao", "chuva", "temperatura", "calor", "frio"}:
            return "weather"
        if word_set & {"noticia", "noticias", "manchete", "manchetes", "jornal"}:
            return "news"
        if word_set & {"fipe", "carro", "veiculo", "veiculos", "moto", "automovel", "caminhonete"}:
            return "vehicles"
        if word_set & {"preco", "valor", "custa", "custaria"} and any(word.isdigit() and len(word) == 4 for word in words):
            return "vehicles"
        if word_set & {"bitcoin", "dolar", "euro", "acao", "acoes", "cotacao", "bolsa", "cripto"}:
            return "finance"
        if word_set & {"jurisprudencia", "juridico", "juridica"}:
            return "legal"
        return "unknown_external"

    def _external_domain_label(self, domain):
        return {
            "weather": "clima",
            "news": "noticias",
            "vehicles": "veiculos",
            "finance": "cotacao",
            "legal": "pesquisa juridica",
            "unknown_external": "informacao externa atual",
        }.get(domain, "informacao externa atual")

    def _looks_like_entity_information_request(self, words):
        word_set = set(words)
        if "sobre" in word_set and (word_set & {"sabe", "saber", "fala", "fale", "falar", "conte", "contar"}):
            return True
        if words[:2] in (["me", "fala"], ["me", "fale"]) and len(words) >= 3:
            return True
        return False

    def _resolve_contextual_target(self, target, session_context):
        target = str(target or "").strip()
        if not target:
            return ""
        resolver = getattr(session_context, "resolve_entity_reference", None)
        if callable(resolver):
            resolved = resolver(target)
            if resolved:
                return resolved
        return target

    def _is_user_relation_target(self, target):
        normalized = self._normalize(target)
        return normalized in {"meu pai", "minha mae", "meus pais", "minha familia"}

    def _wants_technical_output(self, words):
        return bool(set(words) & {"tecnico", "tecnica", "tecnicamente", "debug", "estruturado", "estruturada", "relacoes"})

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
