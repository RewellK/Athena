from dataclasses import asdict, dataclass, field
from datetime import datetime


RuntimeStateName = str


STATE_DESCRIPTIONS = {
    "offline": "Athena ainda nao iniciou o runtime persistente.",
    "starting": "Athena esta iniciando o corpo temporal.",
    "idle": "Athena esta viva, sem tarefa ativa pesada.",
    "awake": "Athena esta acordada e pronta para coordenar tarefas leves.",
    "processing": "Athena esta processando uma tarefa interna.",
    "reflecting": "Athena esta revisando eventos, falhas ou aprendizados.",
    "consolidating_memory": "Athena esta preparando consolidacao de memoria, sem promover automaticamente.",
    "reviewing_learning": "Athena esta organizando candidatos de aprendizado para revisao humana.",
    "awaiting_approval": "Athena aguarda uma decisao humana antes de promover ou executar algo.",
    "safe_mode": "Athena detectou risco ou falha recorrente e limitou operacoes.",
    "shutting_down": "Athena esta encerrando o runtime com seguranca.",
    "stopped": "Athena encerrou o runtime persistente.",
}


STATE_PERMISSIONS = {
    "offline": ["chat_local"],
    "starting": ["heartbeat", "read_local_status"],
    "idle": ["heartbeat", "run_light_workers", "read_local_status"],
    "awake": ["heartbeat", "run_light_workers", "read_local_status"],
    "processing": ["heartbeat", "run_current_task", "read_local_status"],
    "reflecting": ["heartbeat", "process_reflection", "read_local_status"],
    "consolidating_memory": ["heartbeat", "prepare_memory_review", "read_local_status"],
    "reviewing_learning": ["heartbeat", "prepare_learning_review", "read_local_status"],
    "awaiting_approval": ["heartbeat", "read_local_status"],
    "safe_mode": ["heartbeat", "read_only_local_status"],
    "shutting_down": ["safe_shutdown"],
    "stopped": ["chat_local"],
}


STATE_RESTRICTIONS = {
    "offline": ["no_background_workers"],
    "starting": ["no_heavy_llm"],
    "idle": ["no_heavy_llm_by_default", "no_external_action_without_request"],
    "awake": ["no_heavy_llm_by_default", "no_external_action_without_request"],
    "processing": ["bounded_worker_cycle"],
    "reflecting": ["candidates_only_without_human_approval"],
    "consolidating_memory": ["no_sensitive_promotion_without_review"],
    "reviewing_learning": ["candidate_not_confirmed"],
    "awaiting_approval": ["no_auto_promotion"],
    "safe_mode": ["read_only", "pause_nonessential_workers"],
    "shutting_down": ["no_new_tasks"],
    "stopped": ["no_background_workers"],
}


@dataclass
class RuntimeState:
    name: RuntimeStateName = "offline"
    description: str = ""
    entered_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    reason: str = ""
    current_task: str = ""
    permissions: list = field(default_factory=list)
    restrictions: list = field(default_factory=list)

    def __post_init__(self):
        self.description = self.description or STATE_DESCRIPTIONS.get(self.name, self.name)
        self.permissions = list(self.permissions or STATE_PERMISSIONS.get(self.name, []))
        self.restrictions = list(self.restrictions or STATE_RESTRICTIONS.get(self.name, []))

    def to_dict(self):
        payload = asdict(self)
        payload["description"] = payload.get("description") or STATE_DESCRIPTIONS.get(self.name, self.name)
        payload["permissions"] = list(payload.get("permissions") or STATE_PERMISSIONS.get(self.name, []))
        payload["restrictions"] = list(payload.get("restrictions") or STATE_RESTRICTIONS.get(self.name, []))
        return payload

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{key: value for key, value in payload.items() if key in known})


def new_state(name, reason="", current_task=""):
    now = datetime.now().isoformat(timespec="seconds")
    return RuntimeState(
        name=name,
        entered_at=now,
        updated_at=now,
        reason=reason,
        current_task=current_task,
    )
