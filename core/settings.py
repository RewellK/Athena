import json
import os
import threading


DEFAULT_SETTINGS = {
    "useLLM": True,
    "ollamaUrl": "http://localhost:11434/api/generate",
    "ollamaModel": "qwen2.5:3b",
    "voiceEnabled": False,
    "voiceProvider": "macos_say",
    "fallbackVoiceProvider": "macos_say",
    "piperCommand": "piper",
    "piperModelPath": "",
    "piperOutputPath": "voice_output.wav",
    "shortTermMemoryHours": 24,
    "midTermMemoryDays": 7,
    "useRegexFallback": False,
    "autoIngestExternalKnowledge": False,
    "confirmExternalKnowledge": True,
    "enableLegacyParsers": False,
    "agencyEnabled": True,
    "enableAgency": True,
    "enableProactivity": True,
    "humanApprovalRequired": True,
    "autoExecuteActions": False,
    "autoLearnPermanentKnowledge": False,
    "allowCognitiveRegex": False,
    "allowIntentKeywordRules": False,
    "orchestratorInterpretsMeaning": False,
    "foundationLockdown": True,
    "desktopGuiEnabled": True,
    "officialRepositoryUrl": "https://github.com/RewellK/Athena/",
    "projectRoot": ".",
    "gitReadOnly": True,
    "selfCodeAwarenessEnabled": True,
    "gitAwarenessEnabled": True,
    "sqliteBusyTimeoutSeconds": 30,
    "guiBlockConcurrentMessages": True,
    "errorAwarenessEnabled": True,
    "conversationFirst": True,
    "knowledgeExtractionEntryPoint": "learning_route_only",
    "messageReceivedSoundEnabled": True,
    "messageReceivedSoundProvider": "system_beep",
    "debugMode": False,
    "showRouteMetadata": False,
    "useNaturalResponses": True,
    "useFastConversationPath": True,
    "fastPathEnabled": True,
    "fastPathGreetings": True,
    "fastPathEntityQueries": True,
    "useFastMemoryQueryPath": True,
    "fastMemoryResponses": True,
    "fastLocalSmallTalkResponses": True,
    "startupGreetingEnabled": True,
    "startupGreetingSpeak": False,
    "pendingConfirmationBlocksConversation": False,
    "pendingConfirmationTtlSeconds": 300,
    "voiceRate": 180,
    "voiceVolume": 0.8,
    "voiceName": None,
    "voiceProfile": "default",
    "voiceSpeakResponses": True,
    "voiceSpeakStartupGreeting": False,
    "llmTimeoutSeconds": 30,
    "conversationMetricsEnabled": True,
    "reflectionEnabled": True,
    "reflectionUseLlmResponse": False,
    "reflectionStorePath": "logs/reflection_events.jsonl",
    "reflectionSlowRecallMs": 2500,
    "naturalResponseForSmallTalk": True,
    "useLLMIntentResolution": True,
    "allowLocalIntentFallback": False,
    "intentResolutionTimeoutSeconds": 8,
    "useAthenaSemanticLanguage": False,
}


class Settings:

    def __init__(self, path="config/settings.json"):
        self.path = path
        self._lock = threading.RLock()
        self.values = self.load()

    def load(self):
        with self._lock:
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

    def reload(self):
        self.values = self.load()
        return self.values

    def get(self, key, default=None):
        with self._lock:
            return self.values.get(key, default)

    def set(self, key, value):
        with self._lock:
            self.values[key] = value
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            temp_path = self.path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(self.values, file, indent=4, ensure_ascii=False)
            os.replace(temp_path, self.path)
        return value
