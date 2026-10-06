"""Run this problem's mock LLM as a local HTTP server.

    python -m mock_services.llm_server --port 8001 [--failure-rate 0.2 --fenced-rate 0.3 ...]

Then use shared.mock_llm.HTTPLLMClient("http://127.0.0.1:8001") -- it has the
same interface as the in-process client returned by make_llm().
"""

import sys

import mock_services  # noqa: F401
from shared.mock_llm.__main__ import main

if __name__ == "__main__":
    main(["--responder", "mock_services.llm:make_responder", *sys.argv[1:]])
