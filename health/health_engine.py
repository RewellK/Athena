from health.health_snapshot import HealthSnapshot


class HealthEngine:
    """Read-only operational health view for Athena Desktop/Core."""

    def __init__(self, memory=None, llm_provider=None, voice_engine=None, git_awareness_engine=None, error_capture=None):
        self.memory = memory
        self.llm_provider = llm_provider
        self.voice_engine = voice_engine
        self.git_awareness_engine = git_awareness_engine
        self.error_capture = error_capture

    def snapshot(self):
        llm = self._llm_status()
        sqlite = self._sqlite_status()
        voice = self._voice_status()
        git = self._git_status()
        memory = self._memory_status()
        world = self._world_status()
        agency = self._agency_status()
        last_error = self.error_capture.last_error() if self.error_capture else None
        blockers = [llm, sqlite, voice, git]
        overall = "operational" if sqlite.get("status") == "online" else "degraded"
        if any(item.get("status") == "error" for item in blockers):
            overall = "degraded"
        return HealthSnapshot.build(
            overall=overall,
            llm=llm,
            sqlite=sqlite,
            voice=voice,
            git=git,
            memory=memory,
            world=world,
            agency=agency,
            last_error=last_error,
        ).to_dict()

    def _llm_status(self):
        try:
            if not self.llm_provider:
                return {"status": "indisponível", "available": False, "error": "provider ausente"}
            health = self.llm_provider.health_check()
            return {"status": health.get("status", "desconhecida"), "available": bool(health.get("available")), "error": health.get("error", "")}
        except Exception as error:
            return {"status": "error", "available": False, "error": str(error)}

    def _sqlite_status(self):
        try:
            if not self.memory:
                return {"status": "indisponível", "error": "MemoryDB ausente"}
            self.memory.count_memories()
            return {"status": "online", "error": ""}
        except Exception as error:
            return {"status": "error", "error": str(error)}

    def _voice_status(self):
        try:
            if not self.voice_engine:
                return {"status": "indisponível", "enabled": False, "provider": ""}
            return self.voice_engine.status()
        except Exception as error:
            return {"status": "error", "enabled": False, "provider": "", "last_error": str(error)}

    def _git_status(self):
        try:
            if not self.git_awareness_engine:
                return {"status": "indisponível", "available": False, "repository": False}
            summary = self.git_awareness_engine.summary()
            if not summary.get("git_available"):
                return {"status": "indisponível", "available": False, "repository": False, "error": summary.get("error", "")}
            if summary.get("is_git_repository"):
                return {"status": "online", "available": True, "repository": True, "branch": summary.get("current_branch")}
            return {"status": "sem repositório", "available": True, "repository": False}
        except Exception as error:
            return {"status": "error", "available": False, "repository": False, "error": str(error)}

    def _memory_status(self):
        return {
            "memories": self._safe(lambda: self.memory.count_memories()),
            "short_term": self._safe(lambda: self.memory.count_short_term_memory()),
            "mid_term": self._safe(lambda: self.memory.count_mid_term_memory()),
            "long_term": self._safe(lambda: self.memory.count_real_long_term_memory()),
        }

    def _world_status(self):
        return {
            "entities": self._safe(lambda: self.memory.count_entities()),
            "relationships": self._safe(lambda: self.memory.count_world_relationships()),
            "events": self._safe(lambda: self.memory.count_world_events()),
            "states": self._safe(lambda: self.memory.count_entity_states()),
        }

    def _agency_status(self):
        return {
            "intentions": self._safe(lambda: len(self.memory.list_intentions(limit=100000))),
            "plans": self._safe(lambda: len(self.memory.list_plans(limit=100000))),
            "actions": self._safe(lambda: len(self.memory.list_actions(limit=100000))),
        }

    def _safe(self, fn, fallback=0):
        try:
            return fn()
        except Exception:
            return fallback
