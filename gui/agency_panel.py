import customtkinter as ctk


class AgencyPanel(ctk.CTkFrame):
    """Read-only agency summary."""

    def __init__(self, master, athena):
        super().__init__(master)
        self.athena = athena
        self.text = ctk.CTkTextbox(self, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.button = ctk.CTkButton(self, text="Atualizar agência", command=self.refresh)
        self.button.pack(fill="x", padx=8, pady=(0, 8))

    def refresh(self):
        memory = self.athena.memory
        lines = [
            "AGÊNCIA",
            "",
            f"Intenções: {len(memory.list_intentions(limit=100000))}",
            f"Objetivos de agência: {len(memory.list_agency_goals(limit=100000))}",
            f"Planos: {len(memory.list_plans(limit=100000))}",
            f"Ações: {len(memory.list_actions(limit=100000))}",
            f"Outcomes: {len(memory.list_outcomes(limit=100000))}",
            "",
            "Planos recentes:",
        ]
        for item in memory.list_plans(limit=8):
            lines.append(f"- Plano #{item[0]} | status: {item[2]}")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", "\n".join(lines))
        self.text.configure(state="disabled")
