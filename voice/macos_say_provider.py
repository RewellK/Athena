import shutil
import subprocess

from voice.voice_provider import VoiceProvider


class MacOSSayProvider(VoiceProvider):
    provider_id = "macos_say"

    def speak(self, text):
        if not shutil.which("say"):
            raise RuntimeError("comando 'say' não encontrado neste sistema")

        args = ["say"]
        voice_name = self.settings.get("voiceName") if self.settings else None
        profile = self.settings.get("voiceProfile", "default") if self.settings else "default"
        rate = self.settings.get("voiceRate", None) if self.settings else None
        selected_voice = voice_name or (profile if profile and profile != "default" else None)
        if selected_voice:
            args.extend(["-v", str(selected_voice)])
        if rate:
            args.extend(["-r", str(rate)])
        args.append(str(text or ""))
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
