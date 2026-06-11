import threading
import time

from voice.voice_config import VoiceConfig
from voice.voice_manager import VoiceManager


class VoiceEngine:
    """Non-blocking voice facade for Athena responses."""

    def __init__(self, settings, logger=None):
        self.settings = settings
        self.logger = logger
        self.config = VoiceConfig(settings)
        self.manager = VoiceManager(settings, logger)
        self.last_error = ""
        self.last_provider = self.config.provider
        self.last_submit_ms = 0
        self._lock = threading.RLock()

    def speak(self, text):
        if not self.config.enabled or not self.config.speak_responses:
            return False
        return self._submit(text)

    def speak_startup(self, text):
        if not self.config.enabled or not self.config.speak_startup_greeting:
            return False
        return self._submit(text)

    def status(self):
        enabled = bool(self.settings.get("voiceEnabled", False))
        with self._lock:
            return {
                "enabled": enabled,
                "status": "ativa" if enabled else "inativa",
                "provider": self.settings.get("voiceProvider", "macos_say"),
                "fallback_provider": self.settings.get("fallbackVoiceProvider", "macos_say"),
                "last_provider": self.last_provider,
                "last_error": self.last_error,
                "last_submit_ms": self.last_submit_ms,
                "available_providers": self.manager.provider_ids(),
            }

    def _submit(self, text):
        started_at = time.perf_counter()
        thread = threading.Thread(target=self._speak_background, args=(str(text or ""),), daemon=True, name="athena-voice")
        thread.start()
        with self._lock:
            self.last_submit_ms = int((time.perf_counter() - started_at) * 1000)
            self.last_error = ""
            self.last_provider = self.settings.get("voiceProvider", "macos_say")
        return True

    def _speak_background(self, text):
        spoken = self.manager.speak(text)
        with self._lock:
            self.last_provider = self.manager.last_provider
            self.last_error = self.manager.last_error
            self.last_submit_ms = self.manager.last_submit_ms
        if not spoken and self.manager.last_error and self.logger:
            self.logger.log("VOICE_OUTPUT_SKIPPED", self.manager.last_error)
