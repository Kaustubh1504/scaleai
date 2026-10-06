import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from shared.fake_clock import FakeClock
from shared.mock_llm import (
    AsyncHTTPLLMClient,
    ContextLengthExceededError,
    FinalStep,
    HTTPLLMClient,
    KeywordClassifier,
    LLMConfig,
    LLMRateLimitError,
    LLMServerError,
    LLMStreamInterruptedError,
    LLMTimeoutError,
    MockLLMClient,
    MockLLMEngine,
    ScriptedAgent,
    SummarizeResponder,
    ToolStep,
    create_app,
)
from shared.tokens import count_tokens

BILLING = "Classify this ticket. <item>I was charged twice on my invoice</item>"
BUG = "Classify this ticket. <item>The app crashes with an error on login</item>"


def client(**cfg):
    return MockLLMClient(LLMConfig(**cfg), clock=FakeClock())


def test_clean_classification_and_usage():
    c = client()
    resp = c.complete(BILLING)
    assert json.loads(resp.text) == {"label": "billing", "confidence": json.loads(resp.text)["confidence"]}
    assert 0.70 <= json.loads(resp.text)["confidence"] <= 0.99
    assert resp.input_tokens == count_tokens(BILLING)
    assert c.usage.calls == 1 and c.usage.input_tokens == resp.input_tokens
    assert c.usage.cost_usd == pytest.approx((resp.input_tokens * 0.5 + resp.output_tokens * 1.5) / 1000)


def test_instructions_outside_item_tags_are_ignored():
    c = client()
    prompt = "Labels: billing (refund, invoice), bug (crash). <item>hello there</item>"
    assert json.loads(c.complete(prompt).text)["label"] == "other"


def test_batch_items_keep_order():
    c = client()
    items = [{"id": "a", "text": "refund please"}, {"id": "b", "text": "it crashes"}, {"id": "c", "text": "hi"}]
    out = json.loads(c.complete(f"<items>{json.dumps(items)}</items>").text)
    assert [(r["id"], r["label"]) for r in out] == [("a", "billing"), ("b", "bug"), ("c", "other")]


def test_same_seed_is_deterministic_and_attempts_vary():
    def run(seed):
        c = client(seed=seed, failure_rate=0.3, fenced_rate=0.3, inconsistent_rate=0.2)
        out = []
        for _ in range(20):
            try:
                out.append(c.complete(BILLING).text)
            except LLMServerError:
                out.append("ERR")
        return out

    assert run(1) == run(1)
    assert run(1) != run(2)
    assert len(set(run(1))) > 1


def test_fault_script_and_prompt_faults():
    c = client(fault_script={1: "timeout", 2: "rate_limit", 3: "fenced"})
    with pytest.raises(LLMTimeoutError):
        c.complete(BUG)
    with pytest.raises(LLMRateLimitError) as exc:
        c.complete(BUG)
    assert exc.value.retry_after == 1.0
    assert c.complete(BUG).text.startswith("```json")
    assert c.usage.failed_calls == 2 and c.usage.calls == 1

    c = client(prompt_faults={"charged twice": ["malformed", "wrong_label", "ok"]})
    first, second, third = (c.complete(BILLING).text for _ in range(3))
    with pytest.raises(json.JSONDecodeError):
        json.loads(first)
    assert json.loads(second)["label"] not in {"billing", "bug", "feature_request", "other"}
    assert json.loads(third)["label"] == "billing"
    assert json.loads(c.complete(BUG).text)["label"] == "bug"  # other prompts unaffected


def test_fail_first_attempts_is_per_prompt():
    c = client(fail_first_attempts=2)
    for _ in range(2):
        with pytest.raises(LLMServerError):
            c.complete(BILLING)
    assert json.loads(c.complete(BILLING).text)["label"] == "billing"
    with pytest.raises(LLMServerError):
        c.complete(BUG)


def test_rpm_limit_uses_clock():
    clock = FakeClock()
    c = MockLLMClient(LLMConfig(rpm_limit=2, rate_limit_window_s=10), clock=clock)
    c.complete(BILLING)
    clock.advance(4)
    c.complete(BUG)
    with pytest.raises(LLMRateLimitError) as exc:
        c.complete("x")
    assert exc.value.retry_after == pytest.approx(6)
    clock.advance(6)
    c.complete("x")


def test_latency_and_client_timeout():
    clock = FakeClock()
    c = MockLLMClient(LLMConfig(latency_s=2.0), clock=clock)
    start = clock.time()
    c.complete(BILLING)
    assert clock.time() - start == 2.0
    with pytest.raises(LLMTimeoutError):
        c.complete(BUG, timeout=1.0)
    assert clock.time() - start == 3.0
    assert clock.sleeps == []  # mock latency is not recorded as a caller sleep


def test_context_length():
    c = client(max_context_tokens=5)
    with pytest.raises(ContextLengthExceededError):
        c.complete("one two three four five six")


def test_async_complete_concurrently():
    c = client()

    async def main():
        return await asyncio.gather(*(c.acomplete(f"<item>refund {i}</item>") for i in range(10)))

    results = asyncio.run(main())
    assert all(json.loads(r.text)["label"] == "billing" for r in results)


def test_stream_and_disconnect():
    c = MockLLMClient(LLMConfig(), responder=SummarizeResponder(max_words=10), clock=FakeClock())
    text = "<item>" + " ".join(f"w{i}" for i in range(30)) + "</item>"
    assert "".join(c.stream(text)) == "Summary: " + " ".join(f"w{i}" for i in range(10))

    c = MockLLMClient(LLMConfig(stream_disconnect_rate=1.0), responder=SummarizeResponder(), clock=FakeClock())
    got = []
    with pytest.raises(LLMStreamInterruptedError):
        for chunk in c.stream(text):
            got.append(chunk)
    assert "".join(got) != "Summary: " + " ".join(f"w{i}" for i in range(25))


def agent():
    return ScriptedAgent({"weather": [ToolStep("get_weather", {"city": "SF"}), FinalStep("It is sunny.")]})


def test_tool_calling_loop_and_faults():
    c = MockLLMClient(LLMConfig(), responder=agent(), clock=FakeClock())
    messages = [{"role": "user", "content": "What is the weather in SF?"}]
    first = c.chat(messages)
    assert first.content is None and first.tool_calls[0].name == "get_weather"
    assert json.loads(first.tool_calls[0].arguments) == {"city": "SF"}
    messages += [{"role": "assistant", "content": None,
                  "tool_calls": [{"id": first.tool_calls[0].id, "name": "get_weather",
                                  "arguments": first.tool_calls[0].arguments}]},
                 {"role": "tool", "tool_call_id": first.tool_calls[0].id, "content": "sunny"}]
    assert c.chat(messages).content == "It is sunny."

    looping = MockLLMClient(LLMConfig(tool_loop_rate=1.0), responder=agent(), clock=FakeClock())
    assert looping.chat(messages).tool_calls[0].name == "get_weather"  # repeats instead of finishing

    bad = MockLLMClient(LLMConfig(tool_bad_args_rate=1.0), responder=agent(), clock=FakeClock())
    with pytest.raises(json.JSONDecodeError):
        json.loads(bad.chat(messages[:1]).tool_calls[0].arguments)

    unknown = MockLLMClient(LLMConfig(tool_unknown_rate=1.0), responder=agent(), clock=FakeClock())
    assert unknown.chat(messages[:1]).tool_calls[0].name == "get_weather_v2"


def test_custom_keyword_classifier():
    responder = KeywordClassifier({"positive": ["great"], "negative": ["awful"]}, default_label="neutral")
    c = MockLLMClient(responder=responder, clock=FakeClock())
    assert json.loads(c.complete("<item>great and awful</item>").text)["confidence"] < 0.70  # tie
    assert json.loads(c.complete("<item>meh</item>").text)["label"] == "neutral"


# ------------------------------------------------------------------ HTTP


def http_pair(**cfg):
    engine = MockLLMEngine(LLMConfig(**cfg))
    test_client = TestClient(create_app(engine))
    return engine, HTTPLLMClient(http=test_client)


def test_http_complete_and_errors():
    engine, c = http_pair(fault_script={2: "rate_limit", 3: "server_error"}, retry_after_s=2.5)
    assert json.loads(c.complete(BILLING).text)["label"] == "billing"
    with pytest.raises(LLMRateLimitError) as exc:
        c.complete(BILLING)
    assert exc.value.retry_after == 2.5
    with pytest.raises(LLMServerError):
        c.complete(BILLING)
    assert c.usage()["calls"] == 1 and c.usage()["failed_calls"] == 2


def test_http_rate_limit_header():
    engine = MockLLMEngine(LLMConfig(fault_script={1: "rate_limit"}, retry_after_s=2.5))
    r = TestClient(create_app(engine)).post("/v1/complete", json={"prompt": "x"})
    assert r.status_code == 429 and r.headers["Retry-After"] == "3"


def test_http_timeout_and_context_length():
    _, c = http_pair(fault_script={1: "timeout"}, max_context_tokens=50)
    with pytest.raises(LLMTimeoutError):
        c.complete("x", timeout=0.01)
    with pytest.raises(ContextLengthExceededError):
        c.complete("word " * 100)


def test_http_admin_config_patch():
    engine, c = http_pair()
    tc = c._http
    assert tc.patch("/v1/admin/config", json={"failure_rate": 1.0}).status_code == 200
    with pytest.raises(LLMServerError):
        c.complete(BUG)
    assert tc.patch("/v1/admin/config", json={"nope": 1}).status_code == 422


def test_http_stream_sse_and_disconnect():
    engine = MockLLMEngine(LLMConfig(), responder=SummarizeResponder(max_words=6))
    c = HTTPLLMClient(http=TestClient(create_app(engine)))
    assert "".join(c.stream("<item>a b c d e f g h</item>")) == "Summary: a b c d e f"
    engine.config.update(stream_disconnect_rate=1.0)
    with pytest.raises(LLMStreamInterruptedError):
        list(c.stream("<item>a b c d e f g h i j k l</item>"))


def test_http_chat():
    engine = MockLLMEngine(LLMConfig(), responder=agent())
    c = HTTPLLMClient(http=TestClient(create_app(engine)))
    resp = c.chat([{"role": "user", "content": "weather in SF"}])
    assert resp.tool_calls[0].name == "get_weather"


def test_async_http_client():
    engine = MockLLMEngine(LLMConfig(), responder=SummarizeResponder(max_words=3))

    async def main():
        transport = httpx.ASGITransport(app=create_app(engine))
        async with httpx.AsyncClient(transport=transport, base_url="http://llm") as http:
            c = AsyncHTTPLLMClient(http=http)
            resp = await c.acomplete("<item>one two three four</item>")
            chunks = [chunk async for chunk in c.astream("<item>one two three four</item>")]
            return resp.text, "".join(chunks)

    text, streamed = asyncio.run(main())
    assert text == streamed == "Summary: one two three"
