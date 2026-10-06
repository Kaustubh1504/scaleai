"""Command line entry point.

    python -m dispatcher run --once --state-dir state \\
        --events data/events.jsonl --subscriptions data/subscriptions.json

Without --once it keeps polling, calling dispatch_due() every --interval seconds.
Each pass prints its DispatchReport as one JSON line on stdout.
Exit codes: 0 ok, 2 unusable configuration (a bad subscriptions file or unreadable state).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

import httpx

from mock_services.clock import Clock, RealClock

from .dispatcher import Dispatcher
from .events import EventStore
from .state import StateError
from .subscriptions import SubscriptionError, load_subscriptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dispatcher", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="deliver due events")
    run.add_argument("--state-dir", type=Path, required=True)
    run.add_argument("--events", type=Path, required=True)
    run.add_argument("--subscriptions", type=Path, required=True)
    run.add_argument("--once", action="store_true", help="one pass, then exit")
    run.add_argument("--interval", type=float, default=1.0, help="seconds between passes")
    run.add_argument("--max-attempts", type=int, default=5)
    return parser


def main(argv: list[str] | None = None, *, http: httpx.Client | None = None, clock: Clock | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        subscriptions = load_subscriptions(args.subscriptions)
    except SubscriptionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    clock = clock or RealClock()
    with http or httpx.Client() as client:
        try:
            dispatcher = Dispatcher(args.state_dir, EventStore(args.events), subscriptions, client, clock,
                                    max_attempts=args.max_attempts)
        except StateError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        try:
            while True:
                report = dispatcher.dispatch_due()
                print(json.dumps(asdict(report)), flush=True)
                if args.once:
                    return 0
                clock.sleep(args.interval)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
