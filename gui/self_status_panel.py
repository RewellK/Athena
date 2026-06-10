import customtkinter as ctk


class SelfStatusPanel(ctk.CTkFrame):
    """Shows operational status gathered from Athena Core without freezing the GUI."""

    def __init__(self, master, athena, task_runner=None):
        super().__init__(master)
        self.athena = athena
        self.task_runner = task_runner
        self.loading = False
        self.text = ctk.CTkTextbox(self, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.refresh_button = ctk.CTkButton(self, text="Atualizar status", command=self.refresh)
        self.refresh_button.pack(fill="x", padx=8, pady=(0, 8))

    def refresh(self):
        if self.loading:
            return
        self.loading = True
        self.refresh_button.configure(state="disabled")
        self._write("Atualizando status...")

        def work():
            return self.athena.get_desktop_status()

        def success(status):
            self.after(0, lambda: self._render(status))

        def failure(error, _stacktrace):
            friendly = self.athena.handle_exception(error, {"module": "gui/self_status_panel.py", "operation": "refresh"})
            self.after(0, lambda: self._write_done(friendly))

        if self.task_runner:
            self.task_runner.submit(work, on_success=success, on_error=failure, description="status_refresh")
        else:
            try:
                success(work())
            except Exception as error:
                failure(error, "")

    def _render(self, status):
        lines = [
            "STATUS DA ATHENA",
            "",
            f"LLM: {status['llm']['status']}",
            f"Modelo: {status['llm']['model']}",
            f"Erro LLM: {status['llm'].get('error', '') or 'nenhum'}",
            f"Voz: {status['voice']['status']}",
            f"Provider de voz: {status['voice']['provider']}",
            f"Último provider usado: {status['voice'].get('last_provider', '')}",
            f"Último erro de voz: {status['voice'].get('last_error', '') or 'nenhum'}",
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
        last_error = status.get("last_error")
        if last_error:
            lines.extend([
                "",
                "ÚLTIMO ERRO REGISTRADO",
                f"Tipo: {last_error.get('error_type')}",
                f"Gravidade: {last_error.get('analysis', {}).get('severity')}",
                f"Módulo provável: {last_error.get('analysis', {}).get('probable_module')}",
            ])
        self._write_done("\n".join(lines))

    def _write_done(self, text):
        self.loading = False
        self.refresh_button.configure(state="normal")
        self._write(text)

    def _write(self, text):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", text)
        self.text.configure(state="disabled")
