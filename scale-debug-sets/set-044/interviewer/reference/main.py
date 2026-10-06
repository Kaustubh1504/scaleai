import json
import sys

sys.path.insert(0, ".")

from embedclient.report import build_report  # noqa: E402
from tests.mock_server import API_KEY, MockEmbeddingServer  # noqa: E402

if __name__ == "__main__":
    server = MockEmbeddingServer().start()
    try:
        print(json.dumps(build_report(server.url, API_KEY), indent=2))
    finally:
        server.stop()
