import customtkinter as ctk


class SelfStatusPanel(ctk.CTkFrame):
    """Shows operational status gathered from Athena Core."""

    def __init__(self, master, athena):
        super().__init__(master)
        self.athena = athena
        self.text = ctk.CTkTextbox(self, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.refresh_button = ctk.CTkButton(self, text="Atualizar status", command=self.refresh)
        self.refresh_button.pack(fill="x", padx=8, pady=(0, 8))

    def refresh(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        status = self.athena.get_desktop_status()
        lines = [
            "STATUS DA ATHENA",
            "",
            f"LLM: {status['llm']['status']}",
            f"Modelo: {status['llm']['model']}",
            f"Voz: {status['voice']['status']}",
            f"Provider de voz: {status['voice']['provider']}",
            f"Memórias: {status['memory']['memories']}",
            f"Memória curta: {status['memory']['short_term']}",
            f"Memória média: {status['memory']['mid_term']}",
            f"Memória longa: {status['memory']['long_term']}",
            f"Entidades: {status['world']['entities']}",
            f"Relações do mundo: {status['world']['relationships']}",
            f"Eventos do mundo: {status['world']['events']}",
            f"Estados: {status['world']['states']}",
            f"Intenções: {status['agency']['intentions']}",
            f"Planos: {status['agency']['plans']}",
            f"Ações: {status['agency']['actions']}",
            f"Git: {status['git']['summary']}",
        ]
        self.text.insert("end", "\n".join(lines))
        self.text.configure(state="disabled")
