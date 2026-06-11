class VoiceConfig:
    """Typed accessors for voice-related runtime settings."""

    def __init__(self, settings):
        self.settings = settings

    @property
    def enabled(self):
        return bool(self.settings.get("voiceEnabled", False))

    @property
    def provider(self):
        return str(self.settings.get("voiceProvider", "macos_say") or "none")

    @property
    def fallback_provider(self):
        return str(self.settings.get("fallbackVoiceProvider", "macos_say") or "none")

    @property
    def speak_responses(self):
        return bool(self.settings.get("voiceSpeakResponses", True))

    @property
    def speak_startup_greeting(self):
        return bool(
            self.settings.get(
                "voiceSpeakStartupGreeting",
                self.settings.get("startupGreetingSpeak", False),
            )
        )
