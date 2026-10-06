"""Run the mock records API as an HTTP server.

    python -m shared.mock_api --port 9200 --records data/records.json --token-ttl 30 --rpm-limit 10
"""

from __future__ import annotations

import argparse
import json

import uvicorn

from .api import MockRecordsAPI


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9200)
    parser.add_argument("--records", help="JSON file containing a list of records with an 'id' field")
    parser.add_argument("--token-ttl", type=float, default=300.0)
    parser.add_argument("--rpm-limit", type=int, default=None)
    args = parser.parse_args(argv)

    if args.records:
        with open(args.records) as fh:
            records = json.load(fh)
    else:
        records = [{"id": f"rec_{i:04d}", "value": i} for i in range(250)]
    api = MockRecordsAPI(records, token_ttl_s=args.token_ttl, rpm_limit=args.rpm_limit)
    uvicorn.run(api.app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
