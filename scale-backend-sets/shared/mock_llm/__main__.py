"""Run the mock LLM as a local HTTP server.

    python -m shared.mock_llm --port 8001 --seed 7 --failure-rate 0.1 --fenced-rate 0.2
    python -m shared.mock_llm --responder mock_services.llm:make_responder

Change behaviour while it runs:
    curl -X PATCH localhost:8001/v1/admin/config -H 'content-type: application/json' \
         -d '{"rate_limit_rate": 0.5}'
"""

from __future__ import annotations

import argparse
import importlib
from dataclasses import fields

import uvicorn

from .config import LLMConfig
from .engine import MockLLMEngine
from .responders import Responder
from .server import create_app

_FLOAT_FIELDS = [f.name for f in fields(LLMConfig) if f.type in ("float", float)]


def load_responder(spec: str):
    module_name, _, attr = spec.partition(":")
    target = getattr(importlib.import_module(module_name), attr or "make_responder")
    return target if isinstance(target, Responder) else target()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rpm-limit", type=int, default=None)
    parser.add_argument("--max-context-tokens", type=int, default=None)
    parser.add_argument("--responder", help="module:attr of a Responder or a zero-arg factory returning one")
    for name in _FLOAT_FIELDS:
        parser.add_argument("--" + name.replace("_", "-"), type=float, default=None)
    args = parser.parse_args(argv)

    config = LLMConfig(seed=args.seed, rpm_limit=args.rpm_limit, max_context_tokens=args.max_context_tokens)
    for name in _FLOAT_FIELDS:
        value = getattr(args, name)
        if value is not None:
            setattr(config, name, value)
    responder = load_responder(args.responder) if args.responder else None
    uvicorn.run(create_app(MockLLMEngine(config, responder)), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
