import tkinter.messagebox as messagebox
import customtkinter as ctk


class SettingsPanel(ctk.CTkFrame):
    """Runtime settings surface. Boolean flags are edited through checkboxes."""

    BOOLEAN_FLAGS = [
        ("messageReceivedSoundEnabled", "Som ao enviar mensagem", ""),
        ("debugMode", "Modo debug", ""),
        ("showRouteMetadata", "Mostrar rota/tempo no chat", ""),
        ("useNaturalResponses", "Respostas naturais", ""),
        ("useFastConversationPath", "Caminho rápido conversacional", ""),
        ("useLLMIntentResolution", "Resolver intenção com LLM", ""),
        (
            "allowLocalIntentFallback",
            "Fallback local de intenção",
            "Essa opção reativa fallback local para intenção. Use apenas em emergência, pois pode enfraquecer a arquitetura LLM-first.",
        ),
        ("voiceEnabled", "Voz ativa", ""),
        ("useLLM", "Usar LLM", ""),
        ("confirmExternalKnowledge", "Confirmar conhecimento externo", ""),
        (
            "autoIngestExternalKnowledge",
            "Ingestão externa automática",
            "Essa opção permite ingestão automática de conhecimento externo. Recomenda-se manter desligada.",
        ),
        (
            "enableLegacyParsers",
            "Parsers legados",
            "Essa opção reativa parsers antigos. Isso pode violar a arquitetura LLM-first.",
        ),
        (
            "useRegexFallback",
            "Fallback por regex",
            "Essa opção permite fallback por regex. Deve ser usado apenas para emergência.",
        ),
        ("enableAgency", "Agência ativa", ""),
        ("enableProactivity", "Proatividade ativa", ""),
    ]

    VOICE_PROVIDERS = ["piper", "macos_say"]
    SOUND_PROVIDERS = ["system_beep", "terminal_bell"]

    def __init__(self, master, athena, on_refresh=None):
        super().__init__(master)
        self.athena = athena
        self.on_refresh = on_refresh
        self.vars = {}

        self.title = ctk.CTkLabel(self, text="Configurações", font=ctk.CTkFont(size=18, weight="bold"))
        self.title.pack(anchor="w", padx=8, pady=(12, 8))

        self.checkbox_frame = ctk.CTkScrollableFrame(self, height=280)
        self.checkbox_frame.pack(fill="x", padx=8, pady=4)

        for key, label, warning in self.BOOLEAN_FLAGS:
            variable = ctk.BooleanVar(value=bool(self.athena.settings.get(key, False)))
            self.vars[key] = variable
            checkbox = ctk.CTkCheckBox(
                self.checkbox_frame,
                text=label,
                variable=variable,
                command=lambda k=key, w=warning: self.toggle_flag(k, w),
            )
            checkbox.pack(anchor="w", padx=8, pady=4)

        self.voice_frame = ctk.CTkFrame(self)
        self.voice_frame.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(self.voice_frame, text="Provider de voz").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.voice_provider_var = ctk.StringVar(value=str(self.athena.settings.get("voiceProvider", "piper")))
        self.voice_provider_menu = ctk.CTkOptionMenu(
            self.voice_frame,
            values=self.VOICE_PROVIDERS,
            variable=self.voice_provider_var,
            command=self.change_voice_provider,
        )
        self.voice_provider_menu.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        ctk.CTkLabel(self.voice_frame, text="Som de mensagem").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.sound_provider_var = ctk.StringVar(value=str(self.athena.settings.get("messageReceivedSoundProvider", "system_beep")))
        self.sound_provider_menu = ctk.CTkOptionMenu(
            self.voice_frame,
            values=self.SOUND_PROVIDERS,
            variable=self.sound_provider_var,
            command=self.change_sound_provider,
        )
        self.sound_provider_menu.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        self.voice_frame.grid_columnconfigure(1, weight=1)

        self.info = ctk.CTkTextbox(self, wrap="word")
        self.info.pack(fill="both", expand=True, padx=8, pady=8)

        self.refresh_button = ctk.CTkButton(self, text="Atualizar configurações", command=self.refresh)
        self.refresh_button.pack(fill="x", padx=8, pady=(0, 8))

    def toggle_flag(self, key, warning):
        value = bool(self.vars[key].get())
        if value and warning:
            accepted = messagebox.askyesno("Configuração sensível", f"{warning}\n\nDeseja continuar?")
            if not accepted:
                self.vars[key].set(False)
                value = False

        self.athena.settings.set(key, value)

        if key == "enableAgency":
            self.athena.settings.set("agencyEnabled", value)
        if key == "voiceEnabled":
            self.athena.settings.values["voiceEnabled"] = value

        self.refresh()
        if self.on_refresh:
            self.on_refresh()

    def change_voice_provider(self, provider):
        self.athena.settings.set("voiceProvider", provider)
        self.refresh()

    def change_sound_provider(self, provider):
        self.athena.settings.set("messageReceivedSoundProvider", provider)
        self.refresh()

    def refresh(self):
        self.athena.settings.reload()
        for key, variable in self.vars.items():
            variable.set(bool(self.athena.settings.get(key, False)))
        self.voice_provider_var.set(str(self.athena.settings.get("voiceProvider", "piper")))
        self.sound_provider_var.set(str(self.athena.settings.get("messageReceivedSoundProvider", "system_beep")))
        lines = [
            "CONFIGURAÇÕES ATUAIS",
            "",
            f"Som de mensagem: {self.athena.settings.get('messageReceivedSoundEnabled', True)} ({self.athena.settings.get('messageReceivedSoundProvider')})",
            f"Modo debug: {self.athena.settings.get('debugMode')}",
            f"Mostrar metadata de rota: {self.athena.settings.get('showRouteMetadata')}",
            f"Respostas naturais: {self.athena.settings.get('useNaturalResponses')}",
            f"Caminho rápido: {self.athena.settings.get('useFastConversationPath')}",
            f"Resolução de intenção por LLM: {self.athena.settings.get('useLLMIntentResolution')}",
            f"Fallback local de intenção: {self.athena.settings.get('allowLocalIntentFallback')}",
            f"Voz ativa: {self.athena.settings.get('voiceEnabled', True)}",
            f"Provider de voz: {self.athena.settings.get('voiceProvider')}",
            f"Fallback de voz: {self.athena.settings.get('fallbackVoiceProvider')}",
            f"Perfil de voz: {self.athena.settings.get('voiceProfile')}",
            f"Velocidade de voz: {self.athena.settings.get('voiceRate')}",
            f"Volume de voz: {self.athena.settings.get('voiceVolume')}",
            f"LLM ativa: {self.athena.settings.get('useLLM')}",
            f"Modelo LLM: {self.athena.settings.get('ollamaModel')}",
            f"Git somente leitura: {self.athena.settings.get('gitReadOnly')}",
            f"Regex fallback: {self.athena.settings.get('useRegexFallback')}",
            f"Parsers legados: {self.athena.settings.get('enableLegacyParsers')}",
            f"Agência ativa: {self.athena.settings.get('enableAgency')}",
            f"Proatividade ativa: {self.athena.settings.get('enableProactivity')}",
            "",
            "Configurações sensíveis exibem confirmação antes de salvar.",
        ]
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("end", "\n".join(lines))
        self.info.configure(state="disabled")
