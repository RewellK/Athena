from voice.providers.macos_provider import MacOSProvider
from voice.providers.piper_provider import PiperProvider


class VoiceEngine:

    def __init__(self, settings, logger=None):
        self.settings = settings
        self.logger = logger
        self.last_error = ""
        self.last_provider = self.settings.get("voiceProvider", "piper")

    def speak(self, text):
        self.last_error = ""
        self.last_provider = self.settings.get("voiceProvider", "piper")
        if not self.settings.get("voiceEnabled", False):
            return False

        provider_name = self.settings.get("voiceProvider", "piper")
        fallback_name = self.settings.get("fallbackVoiceProvider", "macos_say")

        try:
            self._provider(provider_name).speak(text)
            self.last_provider = provider_name
            return True
        except Exception as error:
            self.last_error = f"{provider_name}: {error}"
            if self.logger:
                self.logger.log("VOICE_PROVIDER_FAILED", f"{provider_name}: {error}")

        try:
            self._provider(fallback_name).speak(text)
            self.last_provider = fallback_name
            return True
        except Exception as error:
            self.last_error = f"{fallback_name}: {error}"
            if self.logger:
                self.logger.log("VOICE_FALLBACK_FAILED", f"{fallback_name}: {error}")

        return False

    def status(self):
        enabled = bool(self.settings.get("voiceEnabled", False))
        return {
            "enabled": enabled,
            "status": "ativa" if enabled else "inativa",
            "provider": self.settings.get("voiceProvider", "piper"),
            "fallback_provider": self.settings.get("fallbackVoiceProvider", "macos_say"),
            "last_provider": self.last_provider,
            "last_error": self.last_error,
        }

    def _provider(self, name):
        if name == "piper":
            return PiperProvider(self.settings, self.logger)

        if name == "macos_say":
            return MacOSProvider(self.settings, self.logger)

        raise ValueError(f"Provider de voz desconhecido: {name}")
