import json

from labelbatch.reports import build_report
from tests.mock_server import API_KEY, MockBatchServer

if __name__ == "__main__":
    server = MockBatchServer().start()
    try:
        print(json.dumps(build_report(server.url, API_KEY), indent=2))
    finally:
        server.stop()
