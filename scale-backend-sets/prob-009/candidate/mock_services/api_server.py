"""Run the Tasks API as a local HTTP server.

    python -m mock_services.api_server --port 9300 [--seed 9 --failure-rate 0.1 --malformed-rate 0.05 --rate-limit 5/2]
    python -m exporter --base-url http://127.0.0.1:9300 --project prj_01 --project prj_02 --out exports/
"""

import argparse

import uvicorn

import mock_services  # noqa: F401
from mock_services.api import make_api
from shared.mock_rest import FaultConfig, RateLimitConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9300)
    parser.add_argument("--seed", type=int, default=9)
    parser.add_argument("--failure-rate", type=float, default=0.0)
    parser.add_argument("--malformed-rate", type=float, default=0.0)
    parser.add_argument("--latency", type=float, default=0.0)
    parser.add_argument("--rate-limit", help="REQUESTS/WINDOW_SECONDS, e.g. 5/2")
    parser.add_argument("--retry-after-format", choices=["seconds", "http-date", "none"], default="seconds")
    args = parser.parse_args()
    rate_limit = None
    if args.rate_limit:
        requests, window = args.rate_limit.split("/")
        rate_limit = RateLimitConfig(int(requests), float(window), retry_after_format=args.retry_after_format)
    api = make_api(args.seed, rate_limit=rate_limit,
                   faults=FaultConfig(seed=args.seed, failure_rate=args.failure_rate,
                                      malformed_rate=args.malformed_rate, latency_s=args.latency))
    uvicorn.run(api.app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
