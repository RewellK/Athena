import os
import shutil
import subprocess

from voice.voice_provider import VoiceProvider


class PiperProvider(VoiceProvider):
    provider_id = "piper"

    def speak(self, text):
        command = self.settings.get("piperCommand", "piper")
        model_path = self.settings.get("piperModelPath", "")
        output_path = self.settings.get("piperOutputPath", "voice_output.wav")

        if not model_path:
            raise RuntimeError("piperModelPath não configurado em config/settings.json")

        process = subprocess.run(
            [command, "--model", model_path, "--output_file", output_path],
            input=str(text or ""),
            text=True,
            capture_output=True,
            timeout=30,
        )

        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or "Piper falhou sem mensagem de erro.")

        if os.name == "posix" and shutil.which("afplay"):
            subprocess.Popen(["afplay", output_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return True
