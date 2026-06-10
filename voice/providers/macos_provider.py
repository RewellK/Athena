import subprocess


class MacOSProvider:

    def __init__(self, settings=None, logger=None):
        self.settings = settings
        self.logger = logger

    def speak(self, text):
        process = subprocess.run(
            ["say", text],
            capture_output=True,
            text=True,
            timeout=30
        )

        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or "macOS say falhou.")

        return True
