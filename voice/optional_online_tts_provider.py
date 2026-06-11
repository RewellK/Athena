import os

from voice.voice_provider import VoiceProvider


class OptionalOnlineTTSProvider(VoiceProvider):
    """Placeholder for future online TTS.

    It deliberately avoids importing SDKs or requiring secrets at startup. If no
    API key is configured, VoiceManager can fall back to a local provider.
    """

    provider_id = "online_tts"

    def speak(self, text):
        api_key = os.environ.get("ATHENA_TTS_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("provider online_tts sem API key configurada")
        raise RuntimeError("provider online_tts ainda não possui executor local configurado")
