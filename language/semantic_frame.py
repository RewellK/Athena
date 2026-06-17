import re
import unicodedata
from dataclasses import asdict, dataclass, field


@dataclass
class SemanticFrame:
    subject: str = ""
    verb: str = ""
    object: str = ""
    context: dict = field(default_factory=dict)
    intent: str = "unknown"
    target: str = ""
    relation_type: str = ""
    owner: str = ""
    domain: str = ""
    scope: str = ""
    required_inputs: list = field(default_factory=list)
    confidence: float = 0.0
    source: str = "local"
    requires_llm: bool = False
    requires_evidence: bool = False
    requires_validation: bool = False
    resolved_object: str = ""
    interpretation_source: str = "local"

    def to_dict(self):
        return asdict(self)


class SemanticFrameExtractor:
    """Local semantic frame extractor backed by learnable patterns."""

    COPULAS = {"e", "eh"}

    def __init__(self, workbench=None, current_user="Rewell", spacy_analyzer=None):
        self.workbench = workbench
        self.current_user = current_user
        self.spacy_analyzer = spacy_analyzer

    def extract(self, utterance, context=None):
        context = dict(context or {})
        spacy_context = self._spacy_context(utterance)
        if spacy_context:
            context["spacy"] = spacy_context
        normalized = self._normalize(utterance)
        words = normalized.split()
        if not words:
            return SemanticFrame(source="local_empty", interpretation_source="local")

        query = self._entity_query_frame(utterance, normalized, words, context)
        if query:
            return query

        external = self._external_frame(utterance, normalized, words)
        if external:
            return external

        learning = self._learning_frame(utterance, normalized, words, context)
        if learning:
            return learning

        return SemanticFrame(
            subject=self.current_user,
            verb="dizer",
            object=str(utterance or "").strip(),
            context=context,
            intent="conversation",
            confidence=0.35,
            source="local_fallback",
            interpretation_source="local",
        )

    def _learning_frame(self, utterance, normalized, words, context):
        if words[0] in {"quem", "qual", "quais", "quanto", "quando", "onde", "como"}:
            return None
        copula_index = next((index for index, word in enumerate(words) if word in self.COPULAS), -1)
        if copula_index <= 0 or copula_index >= len(words) - 1:
            return None
        subject_text = self._display(" ".join(words[:copula_index]))
        object_text = " ".join(words[copula_index + 1 :])
        relation_type = self._relation_type(object_text)
        target = subject_text
        owner = self.current_user if self._has_possessive_owner(object_text) else ""
        if words[0] in {"meu", "minha", "meus", "minhas"}:
            subject_text = self.current_user
            target = self._display(" ".join(words[copula_index + 1 :]))
            object_text = " ".join(words[:copula_index])
            owner = self.current_user
            relation_type = self._relation_type(object_text)
        return SemanticFrame(
            subject=target,
            verb=words[copula_index],
            object=object_text,
            context=context,
            intent="learning_candidate",
            target=target,
            relation_type=relation_type,
            owner=owner,
            confidence=0.78 if relation_type else 0.64,
            source="local_semantic_frame",
            interpretation_source="local_pattern",
        )

    def _entity_query_frame(self, utterance, normalized, words, context):
        target = ""
        scope = ""
        if normalized.startswith(("quem e ", "quem eh ")):
            target = self._display(re.sub(r"^quem e[h]? ", "", normalized).strip(" ?"))
            scope = "identity_or_relation"
        elif "sobre" in words:
            index = words.index("sobre")
            target = self._display(" ".join(words[index + 1 :]).strip(" ?"))
            scope = "all_known_facts"
        elif words[:3] in (["me", "fala", "dela"], ["me", "fale", "dela"], ["fala", "dela", ""]):
            target = "dela"
            scope = "all_known_facts"
        if target in {"Ela", "Ele", "Dela", "Dele", "Nela", "Nele"}:
            resolved = self._resolve_recent_entity(context)
            return SemanticFrame(
                subject=self.current_user,
                verb="quer saber",
                object=target.lower(),
                resolved_object=resolved,
                context=context,
                intent="entity_query",
                target=resolved or target,
                scope=scope or "all_known_facts",
                confidence=0.8 if resolved else 0.48,
                source="local_semantic_frame",
                interpretation_source="conversation_context" if resolved else "local_pattern",
                requires_validation=not bool(resolved),
            )
        if target:
            return SemanticFrame(
                subject=self.current_user,
                verb="quer saber",
                object=f"informações sobre {target}",
                context=context,
                intent="entity_query",
                target=target,
                scope=scope or "all_known_facts",
                confidence=0.76,
                source="local_semantic_frame",
                interpretation_source="local_pattern",
            )
        return None

    def _external_frame(self, utterance, normalized, words):
        word_set = set(words)
        if word_set & {"clima", "tempo", "previsao", "chuva", "temperatura"}:
            required = ["location", "date"]
            date = "tomorrow" if "amanh" in normalized else "today"
            return SemanticFrame(
                subject=self.current_user,
                verb="quer consultar",
                object=str(utterance or "").strip(),
                context={"date": date},
                intent="external_information",
                target="clima",
                domain="weather",
                required_inputs=required,
                confidence=0.82,
                source="local_semantic_frame",
                interpretation_source="local_pattern",
                requires_evidence=True,
            )
        return None

    def _relation_type(self, object_text):
        normalized = self._normalize(object_text)
        patterns = self.workbench.confirmed_patterns() if self.workbench else []
        for pattern in patterns:
            if pattern.get("match_text") and pattern["match_text"] in normalized:
                return pattern.get("relation_type", "")
        defaults = {
            "minha namorada": "girlfriend_of",
            "meu namorado": "boyfriend_of",
            "meu pai": "father_of",
            "minha mae": "mother_of",
            "minha amiga": "friend_of",
            "meu amigo": "friend_of",
        }
        for marker, relation in defaults.items():
            if marker in normalized:
                return relation
        return ""

    def _spacy_context(self, utterance):
        analyzer = getattr(self, "spacy_analyzer", None)
        if not analyzer:
            return {}
        try:
            result = analyzer.analyze(utterance)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    def _has_possessive_owner(self, text):
        words = set(self._normalize(text).split())
        return bool(words & {"meu", "minha", "meus", "minhas"})

    def _resolve_recent_entity(self, context):
        recent = context.get("recent_entities") or []
        if not recent:
            return ""
        first = recent[-1]
        if isinstance(first, dict):
            return first.get("name", "")
        return str(first or "")

    def _display(self, text):
        ignored = {"a", "o", "as", "os", "um", "uma", "sobre"}
        return " ".join(word.capitalize() if word not in ignored else word for word in str(text or "").split() if word not in ignored).strip()

    def _normalize(self, text):
        normalized = unicodedata.normalize("NFKD", str(text or "").strip().lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        chars = []
        for char in normalized:
            chars.append(char if char.isalnum() else " ")
        return " ".join("".join(chars).split())
