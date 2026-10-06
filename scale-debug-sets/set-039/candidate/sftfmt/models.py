from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


ALIASES = {"human": "user", "gpt": "assistant", "bot": "assistant", "sys": "system"}


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass
class Conversation:
    conv_id: str
    messages: list


def normalize_role(raw):
    name = (raw or "").strip().lower()
    return Role(ALIASES.get(name, name))
