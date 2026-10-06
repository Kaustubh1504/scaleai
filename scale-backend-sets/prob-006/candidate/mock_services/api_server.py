"""Run the Projects API as a local HTTP server.

    python -m mock_services.api_server --port 9300 [--seed 6 --token-ttl 30 --failure-rate 0.1 --rate-limit 5/10]
    python -m report --base-url http://127.0.0.1:9300 --out report.json
"""

import argparse

import uvicorn

import mock_services  # noqa: F401
from mock_services.api import make_api
from shared.mock_rest import FaultConfig, RateLimitConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9300)
    parser.add_argument("--seed", type=int, default=6)
    parser.add_argument("--token-ttl", type=float, default=300.0)
    parser.add_argument("--failure-rate", type=float, default=0.0)
    parser.add_argument("--rate-limit", help="REQUESTS/WINDOW_SECONDS, e.g. 5/10")
    args = parser.parse_args()
    rate_limit = None
    if args.rate_limit:
        requests, window = args.rate_limit.split("/")
        rate_limit = RateLimitConfig(int(requests), float(window))
    api = make_api(args.seed, token_ttl_s=args.token_ttl, rate_limit=rate_limit,
                   faults=FaultConfig(seed=args.seed, failure_rate=args.failure_rate))
    uvicorn.run(api.app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
