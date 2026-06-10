import os
from datetime import datetime


class AthenaLogger:

    def __init__(self, log_path="logs/athena.log"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log(self, category, message):
        created_at = datetime.now().isoformat(timespec="seconds")
        line = f"[{created_at}] [{category}] {message}\n"

        with open(self.log_path, "a", encoding="utf-8") as file:
            file.write(line)
