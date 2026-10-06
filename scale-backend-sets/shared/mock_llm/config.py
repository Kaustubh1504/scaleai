"""Configuration for the mock LLM.

Every random decision is drawn from ``random.Random(f"{seed}|{prompt_key}|{attempt}")``
where ``attempt`` counts how many times that exact prompt has been sent. So the
same seed and the same sequence of calls per prompt always behave identically,
regardless of how calls for *different* prompts interleave across threads.

At most one fault is applied per call. Faults are chosen in this order and the
first that triggers wins:

1. ``fault_script`` (by global call number, 1-based)
2. ``prompt_faults`` (by substring of the prompt: the n-th call whose prompt
   contains the substring gets the n-th fault, however the prompt is worded)
3. ``fail_first_attempts`` (server error on each prompt's first N attempts)
4. random rates: transport faults (timeout, rate_limit, server_error), then
   content faults (wrong_label, inconsistent, tool_*), then format faults
   (malformed, fenced, prose_wrapped).

Fault names: ``ok``, ``timeout``, ``rate_limit``, ``server_error``,
``wrong_label``, ``inconsistent``, ``malformed``, ``fenced``, ``prose_wrapped``,
``tool_loop``, ``tool_bad_args``, ``tool_unknown``, ``stream_disconnect``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

TRANSPORT_FAULTS = ("timeout", "rate_limit", "server_error")
CONTENT_FAULTS = ("wrong_label", "inconsistent", "tool_loop", "tool_bad_args", "tool_unknown")
FORMAT_FAULTS = ("malformed", "fenced", "prose_wrapped")
STREAM_FAULTS = ("stream_disconnect",)
ALL_FAULTS = ("ok",) + TRANSPORT_FAULTS + CONTENT_FAULTS + FORMAT_FAULTS + STREAM_FAULTS


@dataclass
class LLMConfig:
    seed: int = 0
    model: str = "mock-llm-1"

    # Latency added to every call, in seconds (on the engine's clock).
    latency_s: float = 0.0
    latency_jitter_s: float = 0.0
    # How long a "timeout" fault hangs when the caller gave no timeout.
    timeout_hang_s: float = 30.0

    # Transport faults (raise an exception / return an HTTP error).
    timeout_rate: float = 0.0
    rate_limit_rate: float = 0.0
    failure_rate: float = 0.0
    # Deterministic rate limit: at most rpm_limit successful calls per window.
    rpm_limit: int | None = None
    rate_limit_window_s: float = 60.0
    retry_after_s: float = 1.0

    # Content faults (the call succeeds but the answer is wrong).
    wrong_label_rate: float = 0.0
    inconsistent_rate: float = 0.0
    tool_loop_rate: float = 0.0
    tool_bad_args_rate: float = 0.0
    tool_unknown_rate: float = 0.0

    # Format faults (the call succeeds but the text is hard to parse).
    malformed_rate: float = 0.0
    fenced_rate: float = 0.0
    prose_wrapped_rate: float = 0.0

    # Streaming.
    stream_disconnect_rate: float = 0.0
    stream_chunk_words: int = 3
    stream_chunk_delay_s: float = 0.0

    # Prompts longer than this many tokens are rejected with HTTP 400.
    max_context_tokens: int | None = None

    # Deterministic scripting for tests.
    fault_script: dict[int, str] = field(default_factory=dict)
    prompt_faults: dict[str, list[str]] = field(default_factory=dict)
    fail_first_attempts: int = 0

    # Pricing, USD per 1,000 tokens.
    input_cost_per_1k: float = 0.50
    output_cost_per_1k: float = 1.50

    def __post_init__(self) -> None:
        for name in list(self.fault_script.values()) + [f for seq in self.prompt_faults.values() for f in seq]:
            if name not in ALL_FAULTS:
                raise ValueError(f"unknown fault {name!r}; expected one of {ALL_FAULTS}")
        # JSON round-trips turn int keys into strings.
        self.fault_script = {int(k): v for k, v in self.fault_script.items()}

    def update(self, **changes) -> None:
        valid = {f.name for f in fields(self)}
        unknown = set(changes) - valid
        if unknown:
            raise ValueError(f"unknown config fields: {sorted(unknown)}")
        for key, value in changes.items():
            setattr(self, key, value)
        self.__post_init__()

    def as_dict(self) -> dict:
        return asdict(self)
