from datetime import datetime


class HealthSnapshot:
    def __init__(self, payload):
        self.payload = payload

    def to_dict(self):
        return dict(self.payload)

    @staticmethod
    def build(**kwargs):
        payload = {"created_at": datetime.now().isoformat(timespec="seconds")}
        payload.update(kwargs)
        return HealthSnapshot(payload)
