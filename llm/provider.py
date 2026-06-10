import json
import urllib.error
import urllib.request


class LLMResult:

    def __init__(self, available, text, error=None):
        self.available = available
        self.text = text
        self.error = error


class OllamaProvider:

    def __init__(self, settings, logger=None):
        self.settings = settings
        self.logger = logger

    def generate(self, prompt):
        if not self.settings.get("useLLM", True):
            return LLMResult(False, "", "LLM desativada em config/settings.json")

        url = self.settings.get("ollamaUrl")
        model = self.settings.get("ollamaModel")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                return LLMResult(True, data.get("response", "").strip())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
            if self.logger:
                self.logger.log("LLM_UNAVAILABLE", str(error))
            return LLMResult(False, "", str(error))
