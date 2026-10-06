from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    job_id: str
    team: str
    priority: int
    release: int
    duration: int
    deps: tuple
    deadline: int | None
    max_retries: int

    def queue_key(self):
        """Higher priority first, then earlier release, then id."""
        return (-self.priority, self.job_id)


class JobState:
    def __init__(self, job, events=[]):
        self.job = job
        self.events = events
        self.status = "pending"
        self.attempts = 0
        self.ready_at = job.release
        self.start = None
        self.end = None
        self.worker = None
        self.busy = 0

    def log(self, text):
        self.events.append(text)
