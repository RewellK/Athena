import threading
import customtkinter as ctk


class ChatPanel(ctk.CTkFrame):
    """Chat UI. It never interprets meaning; it calls Athena.chat."""

    def __init__(self, master, athena):
        super().__init__(master)
        self.athena = athena
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
        message = self.entry.get().strip()
        if not message:
            return
        self.entry.delete(0, "end")
        self._append("Você", message)
        self.send_button.configure(state="disabled")
        threading.Thread(target=self._call_athena, args=(message,), daemon=True).start()

    def _call_athena(self, message):
        try:
            response = self.athena.chat(message)
        except Exception as error:
            response = f"Encontrei uma falha ao conversar pelo desktop: {error}"
        self.after(0, lambda: self._finish_response(response))

    def _finish_response(self, response):
        self._append("Athena", response)
        self.send_button.configure(state="normal")

    def _append(self, speaker, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"\n{speaker}: {text}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")
