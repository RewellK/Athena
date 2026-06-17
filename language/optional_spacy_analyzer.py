class OptionalSpacyAnalyzer:
    """Optional syntax perception organ.

    If spaCy or the configured model is unavailable, this organ returns an empty
    analysis and Athena continues with local patterns.
    """

    def __init__(self, model_name="pt_core_news_sm"):
        self.model_name = model_name
        self._nlp = None
        self.available = False
        try:
            import spacy

            self._nlp = spacy.load(model_name)
            self.available = True
        except Exception:
            self._nlp = None
            self.available = False

    def analyze(self, text):
        if not self._nlp:
            return {"available": False, "model": self.model_name}
        doc = self._nlp(str(text or ""))
        return {
            "available": True,
            "model": self.model_name,
            "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents],
            "tokens": [
                {
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "dep": token.dep_,
                    "head": token.head.text,
                }
                for token in doc
            ],
        }
