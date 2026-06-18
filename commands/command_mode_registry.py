class CommandModeRegistry:
    def __init__(self):
        self._modes = {
            "aprendizagem": {
                "name": "aprendizagem",
                "description": "Observa, filtra e cria candidatos de aprendizado sem consolidar automaticamente.",
                "can_coexist": {"status", "diagnostico"},
                "implemented": True,
            },
            "status": {
                "name": "status",
                "description": "Mostra estado local do runtime e pendências.",
                "can_coexist": {"aprendizagem", "silencio", "diagnostico"},
                "implemented": True,
            },
            "diagnostico": {
                "name": "diagnostico",
                "description": "Verifica saúde interna sem reparar automaticamente.",
                "can_coexist": {"aprendizagem", "status"},
                "implemented": True,
            },
            "silencio": {
                "name": "silencio",
                "description": "Pausa notificações e processos não essenciais.",
                "can_coexist": {"status"},
                "implemented": True,
            },
            "memoria": {"name": "memoria", "description": "Modo futuro para revisão de memórias.", "implemented": False},
            "reuniao": {"name": "reuniao", "description": "Modo futuro para reunião consentida.", "implemented": False},
            "controle": {"name": "controle", "description": "Modo futuro privilegiado com autenticação.", "implemented": False},
            "foco": {"name": "foco", "description": "Modo futuro para reduzir interrupções.", "implemented": False},
        }

    def get(self, name):
        return dict(self._modes.get(str(name or "").strip().lower()) or {})

    def list_modes(self):
        return [dict(item) for item in self._modes.values()]
