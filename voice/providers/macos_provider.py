import subprocess


class MacOSProvider:

    def __init__(self, settings=None, logger=None):
        self.settings = settings
        self.logger = logger

    def speak(self, text):
        args = ["say"]
        if self.settings:
            profile = self.settings.get("voiceProfile", "default")
            rate = self.settings.get("voiceRate", None)
            if profile and profile != "default":
                args.extend(["-v", str(profile)])
            if rate:
                args.extend(["-r", str(rate)])
        args.append(text)
        process = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or "macOS say falhou.")
        return True
