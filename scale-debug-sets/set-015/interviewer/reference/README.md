# SFT Packer

Vendors deliver chat transcripts for supervised fine-tuning in slightly different
shapes. This tool normalises roles, merges split turns, validates the turn order,
truncates long conversations to the token budget and renders each example in the chat
template used for training.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/conversations.json`: a list of conversations: `id`, `source`, `tags`
  (comma-separated string, may be blank) and `messages` (`role`, `content`).
- `data/config.json`: `max_tokens`, `per_message_overhead`, `role_aliases`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Conversation ids and sources: trim and lower-case.
- Roles: trim and lower-case, then map through `role_aliases` (`human` → `user`,
  `gpt`/`bot`/`model` → `assistant`). Any role other than `system`, `user` or
  `assistant` after that rejects the conversation with `unknown_role`.
- Content: a missing or `null` content is the empty string. Any other value, including
  numbers such as `0`, is converted to text and trimmed.
- A message whose content is empty after trimming rejects the conversation with
  `empty_message`.
- Tags: split on commas, trim, lower-case. Empty pieces are not tags.

### Validation

1. Consecutive messages with the same role are merged into one, joining their contents
   with a newline.
2. A `system` message is allowed only as the very first message; anywhere else →
   `misplaced_system`.
3. After the optional system message, roles must alternate `user`, `assistant`, `user`,
   … and the last message must be from the `assistant`; otherwise → `bad_order`.

### Tokens and truncation

4. A message costs (number of whitespace-separated words in its content) +
   `per_message_overhead` tokens. An example's tokens are the sum over its messages.
5. While an example has more than `max_tokens` tokens and more than one user/assistant
   pair, drop the **oldest** user/assistant pair. The system message is never dropped.
6. If it still does not fit → `too_long`. If any pair was dropped the status is
   `truncated`, otherwise `ok`.

### Rendering

7. Each message becomes `<|role|>\n<content>\n`, and each assistant message is followed
   by `<|end|>\n`. An example's text contains only its own messages.

### Report

`sftpack.reports.build_report()` returns:

- `examples`: for each kept conversation: `status`, `tokens`, `turns` (messages kept),
  `text`;
- `rejected`: conversation id → reason;
- `summary`:
  - `sources`: sorted distinct sources over **all** conversations in the file;
  - `tag_counts`: tag → number of conversations in the file (kept or not) with that tag,
    keys sorted;
  - `longest_example`: id of the kept example with the most tokens (ties: highest id).

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
