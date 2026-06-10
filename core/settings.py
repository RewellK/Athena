import json
import os


DEFAULT_SETTINGS = {
    "useLLM": True,
    "ollamaUrl": "http://localhost:11434/api/generate",
    "ollamaModel": "qwen2.5:3b",
    "voiceEnabled": False,
    "voiceProvider": "piper",
    "fallbackVoiceProvider": "macos_say",
    "piperCommand": "piper",
    "piperModelPath": "",
    "piperOutputPath": "voice_output.wav",
    "useRegexFallback": False,
    "autoIngestExternalKnowledge": False,
    "confirmExternalKnowledge": True,
    "enableLegacyParsers": False,
    "agencyEnabled": True,
    "humanApprovalRequired": True,
    "autoExecuteActions": False,
    "autoLearnPermanentKnowledge": False,
    "allowCognitiveRegex": False,
    "allowIntentKeywordRules": False,
    "orchestratorInterpretsMeaning": False,
    "foundationLockdown": True
}


class Settings:

    def __init__(self, path="config/settings.json"):
        self.path = path
        self.values = self.load()

    def load(self):
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(DEFAULT_SETTINGS, file, indent=4, ensure_ascii=False)
            return DEFAULT_SETTINGS.copy()

        with open(self.path, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        merged = DEFAULT_SETTINGS.copy()
        merged.update(loaded)

        if merged != loaded:
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(merged, file, indent=4, ensure_ascii=False)

        return merged

    def get(self, key, default=None):
        return self.values.get(key, default)
