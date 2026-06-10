import customtkinter as ctk

from background_tasks.task_runner import BackgroundTaskRunner
from brain.orchestrator import Athena
from gui.agency_panel import AgencyPanel
from gui.chat_panel import ChatPanel
from gui.memory_panel import MemoryPanel
from gui.self_status_panel import SelfStatusPanel
from gui.settings_panel import SettingsPanel
from gui.world_model_panel import WorldModelPanel


class AthenaDesktopApp(ctk.CTk):
    """Desktop shell for Athena Core. GUI delegates cognition to the same Athena object."""

    def __init__(self):
        super().__init__()
        self.title("Athena Desktop")
        self.geometry("1180x760")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.athena = Athena()
        self.task_runner = BackgroundTaskRunner(self.athena.logger)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.chat_panel = ChatPanel(self, self.athena, self.task_runner, self.refresh_lightweight_panels)
        self.chat_panel.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)

        self.side_tabs = ctk.CTkTabview(self)
        self.side_tabs.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

        self.status_tab = self.side_tabs.add("Status")
        self.memory_tab = self.side_tabs.add("Memória")
        self.world_tab = self.side_tabs.add("Mundo")
        self.agency_tab = self.side_tabs.add("Agência")
        self.settings_tab = self.side_tabs.add("Config")

        self.self_status_panel = SelfStatusPanel(self.status_tab, self.athena, self.task_runner)
        self.self_status_panel.pack(fill="both", expand=True, padx=8, pady=8)

        self.memory_panel = MemoryPanel(self.memory_tab, self.athena)
        self.memory_panel.pack(fill="both", expand=True, padx=8, pady=8)

        self.world_model_panel = WorldModelPanel(self.world_tab, self.athena)
        self.world_model_panel.pack(fill="both", expand=True, padx=8, pady=8)

        self.agency_panel = AgencyPanel(self.agency_tab, self.athena)
        self.agency_panel.pack(fill="both", expand=True, padx=8, pady=8)

        self.settings_panel = SettingsPanel(self.settings_tab, self.athena, self.refresh_all)
        self.settings_panel.pack(fill="both", expand=True, padx=8, pady=8)

        self.refresh_all()

    def refresh_lightweight_panels(self):
        for panel in [self.memory_panel, self.world_model_panel, self.agency_panel, self.settings_panel]:
            try:
                panel.refresh()
            except Exception as error:
                self.athena.handle_exception(error, {"module": "gui/main_window.py", "operation": "refresh_lightweight_panels"})

    def refresh_all(self):
        self.refresh_lightweight_panels()
        try:
            self.self_status_panel.refresh()
        except Exception as error:
            self.athena.handle_exception(error, {"module": "gui/main_window.py", "operation": "refresh_all"})
