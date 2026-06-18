from learning.learning_report_engine import LearningReportEngine


class StudyCommandEngine:
    def __init__(self, daily_review=None, report_engine=None):
        self.daily_review = daily_review
        self.report_engine = report_engine or LearningReportEngine()
        self.last_review_id = ""

    def study(self):
        if not self.daily_review:
            return "Ainda não tenho DailyCognitiveReview conectado."
        result = self.daily_review.study()
        self.last_review_id = result.get("review_id", "")
        candidate_store = getattr(self.report_engine, "candidate_store", None)
        if candidate_store:
            created = len(candidate_store.list(session_id=self.last_review_id, status={"candidate", "edited", "approved", "rejected"}, limit=100000))
        else:
            created = len(result.get("created") or [])
        return (
            "Entendido. Estudei o material disponível de hoje e separei "
            f"{created} candidato(s) para revisão. Nada foi consolidado como memória permanente sem sua aprovação."
        )

    def report(self):
        session_id = self.last_review_id or getattr(self.daily_review, "last_review_id", "")
        return self.report_engine.render(title="Relatório do estudo diário", session_id=session_id or None)
