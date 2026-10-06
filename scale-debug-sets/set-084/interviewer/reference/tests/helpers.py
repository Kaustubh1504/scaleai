import asyncio

from embedjobs.reports import build_report
from tests.mock_server import API_KEY, MockBatchServer


async def instant_sleep(seconds):
    await asyncio.sleep(0)


def run_against_mock():
    server = MockBatchServer().start()
    try:
        report = build_report(server.url, API_KEY, sleep=instant_sleep)
    finally:
        server.stop()
    return server, report


def waits_for(report, label, kind):
    return [w for w in report["waits"] if w[0] == label and w[1] == kind]
