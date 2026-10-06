"""Run the webhook receiver as an HTTP server.

    python -m shared.mock_webhook_receiver --port 9100 --secret whsec_test --fail-first 2

GET /_deliveries lists everything received.
"""

from __future__ import annotations

import argparse

import uvicorn

from .receiver import WebhookReceiver


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--secret")
    parser.add_argument("--fail-first", type=int, default=0, help="answer 500 to the first N requests")
    parser.add_argument("--default-status", type=int, default=200)
    args = parser.parse_args(argv)

    receiver = WebhookReceiver(secret=args.secret, default_status=args.default_status)
    receiver.script([500] * args.fail_first)
    uvicorn.run(receiver.app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
