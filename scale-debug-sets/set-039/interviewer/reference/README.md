# SFT Example Formatter

Turns raw chat logs into supervised fine-tuning examples: roles are normalised, unusable
conversations are rejected, a default system prompt is added where needed, long
conversations are trimmed to the token budget, and each example records the character
spans of the assistant replies (the only text the loss is computed on).

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/conversations.jsonl`: one conversation per line, `{"id", "messages": [{"role", "content"}]}`.
- `data/config.json`: `max_tokens` and `default_system`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Conversation ids: trim, lower-case. Content: trim. Messages with blank content are
  dropped before anything else.
- Roles: trim, lower-case, then map aliases: `human` → `user`, `gpt`/`bot` → `assistant`,
  `sys` → `system`.

### Validation (on the cleaned messages)

- An optional `system` message may come first. Anywhere else it makes the conversation
  `bad_turn_order`.
- If no assistant message remains → `no_assistant`.
- Otherwise the rest must alternate user, assistant, user, assistant … and end with an
  assistant message, else `bad_turn_order`.

### Formatting

- If there is no system message, insert `default_system` (trimmed) as the first message.
- Each message renders as `<|role|>\n` + content + `<|end|>\n`; the example text is the
  concatenation.
- Tokens per message = whitespace-separated words + 2. An example's tokens = sum over its
  messages.
- If the example is over `max_tokens`, drop the oldest user/assistant pair (the first two
  messages after the system prompt) and repeat. The system prompt and the final pair are
  always kept; if that is still over budget the conversation is rejected as `too_long`.
  Exactly `max_tokens` fits.
- `turns_dropped` = number of messages removed by trimming.
- `spans`: for each assistant message, `[start, end)` character offsets of its **content**
  in the text (not the `<|assistant|>\n` header and not `<|end|>`), so `text[start:end]`
  equals the content.

### Report

`sftfmt.reports.build_report()` returns:

- `examples`: `{id: {"text", "tokens", "spans", "turns_dropped"}}`;
- `summary`: `examples` (count), `rejected` (`{id: reason}`, sorted by id),
  `assistant_turns` (assistant messages across all examples, after trimming) and
  `mean_tokens` (1 decimal).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
