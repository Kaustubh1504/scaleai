"""Shared setup for the test files: one mock server and one full sync per test class."""
from embedsync.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class SyncRun:
    def __init__(self):
        self.delays = []
        self.server = MockEmbeddingServer().start()

    async def sleep(self, seconds):
        self.delays.append(seconds)

    def report(self):
        return build_report(self.server.url, API_KEY, sleep=self.sleep)

    def stop(self):
        self.server.stop()
