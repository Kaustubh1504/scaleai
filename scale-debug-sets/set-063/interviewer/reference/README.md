# Turnsmith SFT Export

Turnsmith turns raw support-chat logs into supervised fine-tuning examples in chat
format: a system message followed by alternating user and assistant turns. Long chats are
cut down to a token budget by dropping their oldest exchanges, and some conversations are
held back by tag.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: export settings. `system_prompt` and `max_tokens` (the size budget
  for a whole example) are used by the export. `max_new_tokens` is a generation setting
  for a later eval step and is not used here. `exclude_tags` lists tags to hold back.
- `data/conversations.csv`: one row per conversation (`conv_id`, `source`, `tags`).
  `tags` is a `;`-separated list and may be blank.
- `data/turns.csv`: the raw log, one row per turn (`conv_id`, `turn`, `role`, `text`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Conversation ids: trim and lower-case. Tags: trim and lower-case each entry; empty
  entries (from a blank cell or a trailing `;`) are not tags. A conversation with no tags
  gets the single tag `general`. Excluded tags are compared the same way.
- Turns are ordered by their `turn` number, not by file position.
- Roles are trimmed and lower-cased. `user` and `human` mean user; `assistant`, `gpt` and
  `bot` mean assistant. Any other role (for example `system` or `tool`) is dropped, as is
  any turn with blank text.

### Building an example (conversations in `conversations.csv` order)

1. A conversation with any excluded tag is rejected as `excluded`.
2. Consecutive turns with the same role are merged into one message, joined with `\n`.
3. Leading assistant messages and trailing user messages are removed. If nothing is left,
   the conversation is rejected as `no_pair`.
4. The example is the system message (`system_prompt`, trimmed) followed by those
   messages.
5. A message costs its number of whitespace-separated words plus 4. An example's
   `tokens` is the sum over all its messages, including the system message.
6. While an example costs more than `max_tokens`, drop the **oldest user message and the
   assistant message after it**, so the example still starts with a user message. The
   system message is never dropped. If only one user/assistant exchange is left and it
   still does not fit, the conversation is rejected as `too_long`.

### Output

`turnsmith.export.build_dataset()` returns:

- `examples`: conv id → `messages` (list of `{"role", "content"}`), `tokens`,
  `dropped_messages` (how many messages rule 6 removed) and `tags`.
- `rejected`: conv id → reason.
- `summary`: `examples` (count), `rejected_by_reason`, `tag_counts` (tag → number of
  examples carrying it) and `total_tokens` (sum of `tokens` over examples).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the dataset
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
