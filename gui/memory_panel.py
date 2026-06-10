import customtkinter as ctk


class MemoryPanel(ctk.CTkFrame):
    """Read-only memory summary."""

    def __init__(self, master, athena):
        super().__init__(master)
        self.athena = athena
        self.text = ctk.CTkTextbox(self, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.button = ctk.CTkButton(self, text="Atualizar memória", command=self.refresh)
        self.button.pack(fill="x", padx=8, pady=(0, 8))

    def refresh(self):
        try:
            memory = self.athena.memory
            lines = [
                "MEMÓRIA",
                "",
                f"Memórias gerais: {memory.count_memories()}",
                f"Curto prazo: {memory.count_short_term_memory()}",
                f"Médio prazo: {memory.count_mid_term_memory()}",
                f"Longo prazo: {memory.count_real_long_term_memory()}",
                "",
                "Últimas memórias curtas:",
            ]
            for item in memory.list_short_term_memory(include_expired=False)[-10:]:
                lines.append(f"- {item[1]} | importância {item[5]}")
        except Exception as error:
            lines = [self.athena.handle_exception(error, {"module": "gui/memory_panel.py", "operation": "refresh"})]
        self._write("\n".join(lines))

    def _write(self, text):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", text)
        self.text.configure(state="disabled")
