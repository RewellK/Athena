import os
import sys


class MessageSoundEngine:
    """Small non-critical feedback sound. Failure is always silent."""

    def __init__(self, settings=None, logger=None):
        self.settings = settings
        self.logger = logger
        self.last_error = ""

    def play_received(self):
        self.last_error = ""
        if self.settings and not self.settings.get("messageReceivedSoundEnabled", True):
            return False
        provider = self.settings.get("messageReceivedSoundProvider", "system_beep") if self.settings else "system_beep"
        try:
            if provider == "system_beep":
                sys.stdout.write("\a")
                sys.stdout.flush()
                return True
            if provider == "terminal_bell":
                print("\a", end="", flush=True)
                return True
            return False
        except Exception as error:
            self.last_error = str(error)
            if self.logger:
                self.logger.log("MESSAGE_SOUND_FAILED", str(error))
            return False

    def status(self):
        enabled = bool(self.settings.get("messageReceivedSoundEnabled", True)) if self.settings else True
        return {
            "enabled": enabled,
            "provider": self.settings.get("messageReceivedSoundProvider", "system_beep") if self.settings else "system_beep",
            "last_error": self.last_error,
        }
