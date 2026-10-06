import json

from tests.mock_server import API_KEY, MockVectorServer
from vecsync.reports import build_report

if __name__ == "__main__":
    server = MockVectorServer().start()
    try:
        print(json.dumps(build_report(server.url, API_KEY), indent=2))
    finally:
        server.stop()
