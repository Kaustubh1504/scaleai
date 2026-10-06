import asyncio
from pathlib import Path

from .client import EmbeddingClient
from .config import load_config
from .loader import load_documents
from .usage import billed_tokens, collect_usage

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def document_rows(docs, models, cache, failures):
    rows = {}
    for doc in docs:
        row = {}
        for model in models:
            if doc.text in failures[model]:
                row[model] = failures[model][doc.text]
            else:
                row[model] = {"status": "ok", "dims": len(cache.get(model, doc.text))}
        rows[doc.doc_id] = row
    return rows


def summarize(rows, models, tokens):
    summary = {}
    for model in models:
        statuses = [row[model]["status"] for row in rows.values()]
        summary[model] = {
            "ok": statuses.count("ok"),
            "failed": statuses.count("failed"),
            "billed_tokens": tokens[model],
        }
    return summary


async def run(base_url, api_key, data_dir, sleep):
    config = load_config(data_dir / "config.json")
    docs = load_documents(data_dir / "documents.csv")
    kwargs = {"sleep": sleep} if sleep else {}
    client = EmbeddingClient(base_url, api_key, config, **kwargs)
    failures = {}
    for model in config.models:
        failures[model] = await client.embed_model(model, docs)
    records = await collect_usage(client)
    rows = document_rows(docs, config.models, client.cache, failures)
    return {"documents": rows, "summary": summarize(rows, config.models, billed_tokens(records, config.models))}


def build_report(base_url, api_key, data_dir=None, sleep=None):
    return asyncio.run(run(base_url, api_key, Path(data_dir or DATA_DIR), sleep))
