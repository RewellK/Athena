import time

from voice.macos_say_provider import MacOSSayProvider
from voice.optional_online_tts_provider import OptionalOnlineTTSProvider
from voice.piper_provider import PiperProvider


class NullVoiceProvider:
    provider_id = "none"

    def __init__(self, settings=None, logger=None):
        self.settings = settings
        self.logger = logger

    def speak(self, _text):
        return False


class VoiceManager:
    """Resolves voice providers and handles fallback without blocking cognition."""

    PROVIDERS = {
        "none": NullVoiceProvider,
        "macos_say": MacOSSayProvider,
        "piper": PiperProvider,
        "online_tts": OptionalOnlineTTSProvider,
        "openai_tts": OptionalOnlineTTSProvider,
    }

    def __init__(self, settings, logger=None):
        self.settings = settings
        self.logger = logger
        self.last_error = ""
        self.last_provider = self.settings.get("voiceProvider", "macos_say")
        self.last_submit_ms = 0

    def speak(self, text, provider_name=None, fallback_name=None):
        started_at = time.perf_counter()
        provider_name = provider_name or self.settings.get("voiceProvider", "macos_say")
        fallback_name = fallback_name or self.settings.get("fallbackVoiceProvider", "macos_say")
        self.last_error = ""
        self.last_provider = provider_name

        if provider_name == "none":
            self.last_submit_ms = self._elapsed(started_at)
            return False

        if self._try_provider(provider_name, text):
            self.last_submit_ms = self._elapsed(started_at)
            return True

        if fallback_name and fallback_name != provider_name and fallback_name != "none":
            if self._try_provider(fallback_name, text):
                self.last_provider = fallback_name
                self.last_submit_ms = self._elapsed(started_at)
                return True

        self.last_submit_ms = self._elapsed(started_at)
        return False

    def provider_ids(self):
        return sorted(self.PROVIDERS)

    def _try_provider(self, provider_name, text):
        try:
            provider = self._provider(provider_name)
            spoken = bool(provider.speak(text))
            if spoken:
                self.last_provider = provider_name
            return spoken
        except Exception as error:
            self.last_error = f"{provider_name}: {error}"
            if self.logger:
                self.logger.log("VOICE_PROVIDER_FAILED", self.last_error)
            return False

    def _provider(self, name):
        provider_cls = self.PROVIDERS.get(str(name or "none"))
        if not provider_cls:
            raise ValueError(f"Provider de voz desconhecido: {name}")
        return provider_cls(self.settings, self.logger)

    def _elapsed(self, started_at):
        return int((time.perf_counter() - started_at) * 1000)
