from datetime import datetime, timedelta


class FreshnessEngine:
    DEFAULT_TTLS = {
        "weather": 1800,
        "news": 900,
        "finance": 300,
        "vehicles": 86400,
        "sports": 900,
        "places": 86400,
        "documentation": 604800,
        "general_web": 3600,
    }

    def ttl_for(self, domain, source=None):
        source = source or {}
        try:
            ttl = int(source.get("freshness_ttl_seconds") or 0)
        except (TypeError, ValueError):
            ttl = 0
        return ttl if ttl > 0 else self.DEFAULT_TTLS.get(domain, 3600)

    def valid_until(self, fetched_at, domain, source=None):
        fetched = self._parse(fetched_at) or datetime.now()
        return (fetched + timedelta(seconds=self.ttl_for(domain, source))).isoformat(timespec="seconds")

    def is_fresh(self, evidence):
        evidence = evidence or {}
        valid_until = self._parse(evidence.get("valid_until"))
        if not valid_until:
            return False
        return datetime.now() <= valid_until

    def _parse(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None
