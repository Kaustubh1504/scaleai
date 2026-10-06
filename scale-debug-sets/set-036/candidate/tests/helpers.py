from tests.mock_server import API_KEY, MockEmbeddingServer
from vecsync.reports import build_report


class Waits(list):
    """Async stand-in for asyncio.sleep that records each requested delay."""

    async def __call__(self, seconds):
        self.append(seconds)


def run_against_mock():
    server = MockEmbeddingServer().start()
    waits = Waits()
    report = build_report(server.url, API_KEY, sleep=waits)
    return server, waits, report
