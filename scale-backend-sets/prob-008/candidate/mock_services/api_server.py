"""Run the contributor platform API as a local HTTP server.

    python -m mock_services.api_server --port 9300 [--seed 8 --clean --failure-rate 0.1 --rate-limit 5/2]
    python -m earnings --base-url http://127.0.0.1:9300 --start 2024-04-01 --end 2024-04-15 --out earnings.csv

    curl -s localhost:9300/oauth/token -H 'content-type: application/json' \
         -d '{"client_id": "finance", "client_secret": "finance-secret"}'
    curl -s 'localhost:9300/v1/annotators?limit=5' -H "Authorization: Bearer <token>"
"""

import argparse

import uvicorn

import mock_services  # noqa: F401
from mock_services.api import SEED, make_api
from shared.mock_rest import FaultConfig, RateLimitConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9300)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--clean", action="store_true", help="serve canonical (non-messy) records")
    parser.add_argument("--token-ttl", type=float, default=300.0)
    parser.add_argument("--failure-rate", type=float, default=0.0)
    parser.add_argument("--malformed-rate", type=float, default=0.0)
    parser.add_argument("--rate-limit", help="REQUESTS/WINDOW_SECONDS, e.g. 5/2")
    args = parser.parse_args()
    rate_limit = None
    if args.rate_limit:
        requests, window = args.rate_limit.split("/")
        rate_limit = RateLimitConfig(int(requests), float(window))
    api = make_api(args.seed, messy=not args.clean, token_ttl_s=args.token_ttl, rate_limit=rate_limit,
                   faults=FaultConfig(seed=args.seed, failure_rate=args.failure_rate,
                                      malformed_rate=args.malformed_rate))
    uvicorn.run(api.app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
