from datetime import date


class DailyCognitiveReview:
    def __init__(self, day_buffer=None, harvest_worker=None, candidate_store=None):
        self.day_buffer = day_buffer
        self.harvest_worker = harvest_worker
        self.candidate_store = candidate_store
        self.last_review_id = ""

    def study(self, day=None):
        if not self.day_buffer or not self.harvest_worker:
            return {"status": "missing_daily_learning_organs", "created": []}
        day = day or date.today().isoformat()
        self.day_buffer.mark_studying(day)
        entries = self.day_buffer.entries(day=day, limit=500)
        session_id = f"daily:{day}"
        created = self.harvest_worker.harvest_entries(session_id, entries, source="daily_review")
        self.last_review_id = session_id
        self.day_buffer.mark_reviewed(review_id=session_id, day=day)
        return {"status": "reviewed", "review_id": session_id, "created": created, "entries": len(entries)}
