import customtkinter as ctk


class SettingsPanel(ctk.CTkFrame):
    """Runtime settings surface. Cognition remains inside Athena Core."""

    def __init__(self, master, athena, on_refresh=None):
        super().__init__(master)
        self.athena = athena
        self.on_refresh = on_refresh
        self.voice_var = ctk.BooleanVar(value=bool(self.athena.settings.get("voiceEnabled", True)))

        self.voice_switch = ctk.CTkSwitch(self, text="Voz ativa", variable=self.voice_var, command=self.toggle_voice)
        self.voice_switch.pack(anchor="w", padx=8, pady=(12, 8))

        self.info = ctk.CTkTextbox(self, wrap="word")
        self.info.pack(fill="both", expand=True, padx=8, pady=8)

        self.refresh_button = ctk.CTkButton(self, text="Atualizar configurações", command=self.refresh)
        self.refresh_button.pack(fill="x", padx=8, pady=(0, 8))

    def toggle_voice(self):
        value = bool(self.voice_var.get())
        self.athena.settings.set("voiceEnabled", value)
        self.athena.settings.values["voiceEnabled"] = value
        self.refresh()
        if self.on_refresh:
            self.on_refresh()

    def refresh(self):
        self.voice_var.set(bool(self.athena.settings.get("voiceEnabled", True)))
        lines = [
            "CONFIGURAÇÕES",
            "",
            f"Voz ativa: {self.athena.settings.get('voiceEnabled', True)}",
            f"Provider de voz: {self.athena.settings.get('voiceProvider')}",
            f"Fallback de voz: {self.athena.settings.get('fallbackVoiceProvider')}",
            f"LLM ativa: {self.athena.settings.get('useLLM')}",
            f"Modelo LLM: {self.athena.settings.get('ollamaModel')}",
            f"Git somente leitura: {self.athena.settings.get('gitReadOnly')}",
        ]
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("end", "\n".join(lines))
        self.info.configure(state="disabled")
