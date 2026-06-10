import customtkinter as ctk


class WorldModelPanel(ctk.CTkFrame):
    """Read-only World Model summary."""

    def __init__(self, master, athena):
        super().__init__(master)
        self.athena = athena
        self.text = ctk.CTkTextbox(self, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.button = ctk.CTkButton(self, text="Atualizar mundo", command=self.refresh)
        self.button.pack(fill="x", padx=8, pady=(0, 8))

    def refresh(self):
        memory = self.athena.memory
        lines = [
            "WORLD MODEL",
            "",
            f"Entidades: {memory.count_entities()}",
            f"Relações: {memory.count_world_relationships()}",
            f"Eventos: {memory.count_world_events()}",
            f"Estados: {memory.count_entity_states()}",
            "",
            "Entidades recentes:",
        ]
        for item in memory.list_entities()[-12:]:
            lines.append(f"- {item[0]} ({item[1]})")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", "\n".join(lines))
        self.text.configure(state="disabled")
