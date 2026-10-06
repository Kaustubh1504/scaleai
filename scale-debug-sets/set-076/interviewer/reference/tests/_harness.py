from tests.mock_server import API_KEY, MockEmbeddingServer
from vecsync.reports import build_report


class SleepRecorder:
    def __init__(self):
        self.delays = []

    async def __call__(self, delay):
        self.delays.append(delay)


def run_job():
    """Start a fresh mock server, run the whole job against it, return (server, sleeps, report)."""
    server = MockEmbeddingServer().start()
    sleeps = SleepRecorder()
    try:
        report = build_report(server.url, API_KEY, sleep=sleeps)
    except Exception:
        server.stop()
        raise
    return server, sleeps, report
