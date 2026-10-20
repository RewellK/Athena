import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import customtkinter as ctk


class SettingsPanel(ctk.CTkFrame):
    """Runtime settings surface. Boolean flags are edited through checkboxes."""

    BOOLEAN_FLAGS = [
        ('useLLM','Modelo local ativo',''),
        ('localAutonomyEnabled','Executar ferramentas locais',''),
        ('autonomousLocalSkillLearning','Aprender procedimentos verificados',''),
        ('residentGoalsEnabled','Executar objetivos colocados na fila',''),
        ('computerToolsEnabled','Usar aplicativos do macOS',''),
        ('browserToolsEnabled','Navegador isolado',''),
        ('browserInteractionEnabled','Preencher campos e clicar em botões',''),
        ('allowExternalRequests','Consultar páginas públicas',''),
        ('voiceEnabled','Voz ativa',''),
        ('voiceSpeakResponses','Falar respostas',''),
        ('localSpeechInputEnabled','Entrada de voz local',''),
        ('voiceAutoSend','Enviar fala sem revisar transcrição',''),
        ('messageReceivedSoundEnabled','Som ao enviar mensagem',''),
        ('showRouteMetadata','Mostrar detalhes da execução',''),
    ]

    VOICE_PROVIDERS = ["none", "macos_say", "piper"]
    SOUND_PROVIDERS = ["system_beep", "terminal_bell"]
    MODEL_PROFILES = {"Experimental (2B)":"qwen3.5:2b", "Mais capacidade (4B)":"qwen3.5:4b", "Compatibilidade (3B)":"qwen2.5:3b"}

    def __init__(self, master, athena, on_refresh=None):
        super().__init__(master)
        self.athena = athena
        self.on_refresh = on_refresh
        self.vars = {}

        self.title = ctk.CTkLabel(self, text="Configurações", font=ctk.CTkFont(size=18, weight="bold"))
        self.title.pack(anchor="w", padx=8, pady=(12, 8))

        self.folder_button=ctk.CTkButton(self,text='Autorizar pasta de trabalho...',command=self.authorize_folder)
        self.folder_button.pack(fill='x',padx=8,pady=4)
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
        self.voice_provider_var = ctk.StringVar(value=str(self.athena.settings.get("voiceProvider", "macos_say")))
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
        ctk.CTkLabel(self.voice_frame,text='Modelo local').grid(row=2,column=0,sticky='w',padx=8,pady=4)
        self.model_var=ctk.StringVar(value=self.model_label())
        self.model_menu=ctk.CTkOptionMenu(self.voice_frame,values=list(self.MODEL_PROFILES),variable=self.model_var,command=self.change_model)
        self.model_menu.grid(row=2,column=1,sticky='ew',padx=8,pady=4)
        self.voice_frame.grid_columnconfigure(1, weight=1)

        self.info = ctk.CTkTextbox(self, wrap="word")
        self.info.pack(fill="both", expand=True, padx=8, pady=8)

        self.refresh_button = ctk.CTkButton(self, text="Atualizar configurações", command=self.refresh)
        self.refresh_button.pack(fill="x", padx=8, pady=(0, 8))

    def authorize_folder(self):
        folder=filedialog.askdirectory(title='Escolha uma pasta que Athena poderá ler e criar arquivos')
        if folder:
            roots=dict(self.athena.settings.get('fileRoots',{}))
            roots['user']=folder
            self.athena.settings.set('fileRoots',roots)
            self.refresh()

    def model_label(self):
        selected=self.athena.settings.get('ollamaModel')
        return next((label for label,model in self.MODEL_PROFILES.items() if model==selected),str(selected))

    def change_model(self,label):
        self.athena.settings.set('ollamaModel',self.MODEL_PROFILES[label])
        self.refresh()

    def toggle_flag(self, key, warning):
        value = bool(self.vars[key].get())
        if value and warning:
            accepted = messagebox.askyesno("Configuração sensível", f"{warning}\n\nDeseja continuar?")
            if not accepted:
                self.vars[key].set(False)
                value = False

        self.athena.settings.set(key, value)
        if not value and key in {'useLLM','localAutonomyEnabled','residentGoalsEnabled'}:
            self.athena.cancel_current_turn(reason='pause')
        if not value and key=='voiceEnabled':
            self.athena.voice_engine.stop()

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
        self.voice_provider_var.set(str(self.athena.settings.get("voiceProvider", "macos_say")))
        self.model_var.set(self.model_label())
        self.sound_provider_var.set(str(self.athena.settings.get("messageReceivedSoundProvider", "system_beep")))
        lines = [
            "CONFIGURAÇÕES ATUAIS",
            "",
            f"Som de mensagem: {self.athena.settings.get('messageReceivedSoundEnabled', True)} ({self.athena.settings.get('messageReceivedSoundProvider')})",
            f"Modo debug: {self.athena.settings.get('debugMode')}",
            f"Mostrar metadata de rota: {self.athena.settings.get('showRouteMetadata')}",
            f"Respostas naturais: {self.athena.settings.get('useNaturalResponses')}",
            f"Caminho rápido: {self.athena.settings.get('useFastConversationPath')}",
            f"Fast paths ativos: {self.athena.settings.get('fastPathEnabled')}",
            f"Fast path saudação: {self.athena.settings.get('fastPathGreetings')}",
            f"Fast path consulta local: {self.athena.settings.get('fastPathEntityQueries')}",
            f"Resolução de intenção por LLM: {self.athena.settings.get('useLLMIntentResolution')}",
            f"Fallback local de intenção: {self.athena.settings.get('allowLocalIntentFallback')}",
            f"Voz ativa: {self.athena.settings.get('voiceEnabled', False)}",
            f"Falar respostas: {self.athena.settings.get('voiceSpeakResponses')}",
            f"Falar saudação inicial: {self.athena.settings.get('voiceSpeakStartupGreeting')}",
            f"Provider de voz: {self.athena.settings.get('voiceProvider')}",
            f"Fallback de voz: {self.athena.settings.get('fallbackVoiceProvider')}",
            f"Nome da voz: {self.athena.settings.get('voiceName')}",
            f"Perfil de voz: {self.athena.settings.get('voiceProfile')}",
            f"Velocidade de voz: {self.athena.settings.get('voiceRate')}",
            f"Volume de voz: {self.athena.settings.get('voiceVolume')}",
            f"Saudação inicial GUI: {self.athena.settings.get('startupGreetingEnabled')}",
            f"Voz na saudação inicial: {self.athena.settings.get('startupGreetingSpeak')}",
            f"Confirmação pendente bloqueia conversa: {self.athena.settings.get('pendingConfirmationBlocksConversation')}",
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
