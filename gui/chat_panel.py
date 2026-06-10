import customtkinter as ctk


class ChatPanel(ctk.CTkFrame):
    """Chat UI. It never interprets meaning; it calls Athena.chat in a controlled background queue."""

    def __init__(self, master, athena, task_runner=None, on_message_processed=None):
        super().__init__(master)
        self.athena = athena
        self.task_runner = task_runner
        self.on_message_processed = on_message_processed
        self.processing = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.title = ctk.CTkLabel(self, text="Athena", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))

        self.chat_box = ctk.CTkTextbox(self, wrap="word")
        self.chat_box.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=6)
        self.chat_box.insert("end", "Athena Desktop iniciada.\n")
        self.chat_box.configure(state="disabled")

        self.entry = ctk.CTkEntry(self, placeholder_text="Digite sua mensagem para Athena...")
        self.entry.grid(row=2, column=0, sticky="ew", padx=(12, 6), pady=(6, 12))
        self.entry.bind("<Return>", self._send_event)

        self.send_button = ctk.CTkButton(self, text="Enviar", command=self.send_message)
        self.send_button.grid(row=2, column=1, sticky="e", padx=(6, 12), pady=(6, 12))

    def _send_event(self, _event):
        self.send_message()

    def send_message(self):
        if self.processing and self.athena.settings.get("guiBlockConcurrentMessages", True):
            self._append("Athena", "Ainda estou processando sua mensagem anterior. Aguarde a resposta antes de enviar outra.")
            return

        message = self.entry.get().strip()
        if not message:
            return

        self.entry.delete(0, "end")
        self._append("Você", message)
        self._set_processing(True)

        def work():
            return self.athena.chat(message)

        def success(response):
            self.after(0, lambda: self._finish_response(response))

        def failure(error, _stacktrace):
            friendly = self.athena.handle_exception(error, {"module": "gui/chat_panel.py", "operation": "send_message"})
            self.after(0, lambda: self._finish_response(friendly))

        if self.task_runner:
            self.task_runner.submit(work, on_success=success, on_error=failure, description="gui_chat_message")
        else:
            try:
                success(work())
            except Exception as error:
                failure(error, "")

    def _set_processing(self, value):
        self.processing = value
        state = "disabled" if value else "normal"
        self.send_button.configure(state=state)
        self.entry.configure(state=state)

    def _finish_response(self, response):
        self._append("Athena", response)
        self._set_processing(False)
        if self.on_message_processed:
            self.on_message_processed()

    def _append(self, speaker, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"\n{speaker}: {text}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")
