import json

from relaygrade.reports import build_report
from tests.mock_server import API_KEY, MockRelayServer

if __name__ == "__main__":
    server = MockRelayServer().start()
    try:
        print(json.dumps(build_report(server.url, API_KEY), indent=2))
    finally:
        server.stop()
