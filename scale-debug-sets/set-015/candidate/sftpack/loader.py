import json

from .turns import Message


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def clean_content(value):
    return str(value or "").strip()


def load_conversations(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    conversations = []
    for item in raw:
        conversations.append({
            "id": item["id"].strip().lower(),
            "source": (item.get("source") or "").strip().lower(),
            "tags": item.get("tags") or "",
            "messages": [Message(m.get("role") or "", clean_content(m.get("content"))) for m in item["messages"]],
        })
    return conversations
