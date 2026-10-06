"""Run the Scale-flavoured mock REST API as a local HTTP server.

    python -m shared.mock_rest --port 9300 --seed 7 --failure-rate 0.05 --rate-limit 10/1 --token-ttl 60

    curl -s -XPOST localhost:9300/oauth/token -H 'content-type: application/json' \
         -d '{"client_id": "client", "client_secret": "secret"}'
    curl -s localhost:9300/v1/projects -H "Authorization: Bearer <token>"
"""

from __future__ import annotations

import argparse

import uvicorn

from .api import MockRestAPI
from .config import AuthConfig, FaultConfig, RateLimitConfig


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--auth", choices=["oauth", "api_key", "none"], default="oauth")
    parser.add_argument("--token-ttl", type=float, default=300.0)
    parser.add_argument("--rate-limit", help="REQUESTS/WINDOW_SECONDS, e.g. 10/1")
    parser.add_argument("--retry-after-format", choices=["seconds", "http-date", "none"], default="seconds")
    parser.add_argument("--failure-rate", type=float, default=0.0)
    parser.add_argument("--rate-limit-rate", type=float, default=0.0)
    parser.add_argument("--malformed-rate", type=float, default=0.0)
    parser.add_argument("--latency", type=float, default=0.0)
    parser.add_argument("--clean", action="store_true", help="serve canonical records without field mess")
    args = parser.parse_args(argv)

    rate_limit = None
    if args.rate_limit:
        requests, window = args.rate_limit.split("/")
        rate_limit = RateLimitConfig(int(requests), float(window), retry_after_format=args.retry_after_format)
    from .dataset import scale_resources

    api = MockRestAPI(
        scale_resources(args.seed, messy=not args.clean),
        auth=AuthConfig(mode=args.auth, token_ttl_s=args.token_ttl),
        rate_limit=rate_limit,
        faults=FaultConfig(seed=args.seed, failure_rate=args.failure_rate, rate_limit_rate=args.rate_limit_rate,
                           malformed_rate=args.malformed_rate, latency_s=args.latency),
    )
    uvicorn.run(api.app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
