import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class ExternalResearchJob:
    domain: str
    query: str
    source_id: str
    user_message: str = ""
    request: dict = field(default_factory=dict)
    status: str = "pending"
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    started_at: str = ""
    completed_at: str = ""
    result: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self):
        return asdict(self)


class AsyncExternalResearchWorker:
    """Small local queue. It does not spawn threads by default."""

    def __init__(self, evidence_engine=None, connectors=None, timeout_seconds=15, logger=None):
        self.evidence_engine = evidence_engine
        self.connectors = connectors or {}
        self.timeout_seconds = timeout_seconds
        self.logger = logger
        self.jobs = []

    def enqueue(self, domain, query, source, request=None):
        source = dict(source or {})
        job = ExternalResearchJob(
            domain=domain,
            query=query,
            source_id=source.get("source_id", ""),
            user_message=query,
            request=dict(request or {}),
        )
        job.source = source
        self.jobs.append(job)
        return job.to_dict()

    def pending_count(self):
        return len([job for job in self.jobs if job.status == "pending"])

    def process_pending_once(self):
        job = next((item for item in self.jobs if item.status == "pending"), None)
        if not job:
            return None

        job.status = "running"
        job.started_at = datetime.now().isoformat(timespec="seconds")
        started_at = time.perf_counter()
        try:
            connector = self.connectors.get(job.source.get("connector_type")) or self.connectors.get(job.source_id)
            if not connector:
                raise RuntimeError("Nenhum conector habilitado para essa fonte.")
            try:
                raw_result = connector.fetch(
                    job.query,
                    timeout_seconds=self.timeout_seconds,
                    request=job.request,
                    source=job.source,
                )
            except TypeError:
                raw_result = connector.fetch(job.query, timeout_seconds=self.timeout_seconds)
            if time.perf_counter() - started_at > self.timeout_seconds:
                raise TimeoutError("Consulta excedeu o tempo limite.")
            job.result = raw_result or {}
            if self.evidence_engine:
                job.evidence = self.evidence_engine.create_record(job.source, job.query, job.result)
            job.status = "completed"
        except Exception as error:
            job.error = str(error)
            job.status = "failed"
        finally:
            job.completed_at = datetime.now().isoformat(timespec="seconds")
        return job.to_dict()

    def list_jobs(self):
        return [job.to_dict() for job in self.jobs]
