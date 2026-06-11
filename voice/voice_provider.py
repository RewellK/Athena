class VoiceProvider:
    """Small interface implemented by concrete TTS providers."""

    provider_id = "base"

    def __init__(self, settings=None, logger=None):
        self.settings = settings
        self.logger = logger

    def speak(self, text):
        raise NotImplementedError
