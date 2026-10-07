import asyncio

from relaygrade.reports import build_report
from tests.mock_server import API_KEY, MockRelayServer


class SleepRecorder:
    def __init__(self):
        self.delays = []

    async def __call__(self, seconds):
        self.delays.append(seconds)
        await asyncio.sleep(0)


def run_against_mock():
    server = MockRelayServer().start()
    sleep = SleepRecorder()
    try:
        report = build_report(server.url, API_KEY, sleep=sleep)
    finally:
        server.stop()
    return server, report, sleep
