class LearningReviewQueue:
    def __init__(self, candidate_store=None):
        self.candidate_store = candidate_store

    def pending(self, limit=20):
        if not self.candidate_store:
            return []
        return self.candidate_store.list(status={"candidate", "edited"}, limit=limit)

    def count_pending(self):
        return len(self.pending(limit=100000))
